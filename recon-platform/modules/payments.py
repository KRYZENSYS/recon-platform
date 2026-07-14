"""Stripe payment integration"""
import os
import stripe
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, User, Subscription, Payment, Invoice

logger = logging.getLogger(__name__)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

payments_bp = Blueprint("payments", __name__, url_prefix="/api/v1/payments")


@payments_bp.route("/create-checkout-session", methods=["POST"])
@login_required
def create_checkout():
    if not stripe.api_key: return jsonify({"error": "Stripe not configured"}), 503
    data = request.json
    plan = data.get("plan", "pro_monthly")
    price_id = os.getenv(f"STRIPE_{plan.upper()}_PRICE_ID")
    if not price_id: return jsonify({"error": "Plan not available"}), 400
    try:
        if not getattr(current_user, 'stripe_customer_id', None):
            customer = stripe.Customer.create(email=current_user.email, name=current_user.full_name or current_user.username, metadata={"user_id": current_user.id})
            current_user.stripe_customer_id = customer.id
            db.session.commit()
        session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id, payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}], mode="subscription",
            success_url=data.get("success_url", "https://recon.kryzensys.com/dashboard?payment=success") + "&session_id={CHECKOUT_SESSION_ID}",
            cancel_url=data.get("cancel_url", "https://recon.kryzensys.com/pricing?payment=cancelled"),
            metadata={"user_id": current_user.id, "plan": plan}, allow_promotion_codes=True,
        )
        return jsonify({"checkout_url": session.url, "session_id": session.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@payments_bp.route("/create-portal-session", methods=["POST"])
@login_required
def create_portal():
    if not current_user.stripe_customer_id: return jsonify({"error": "No subscription"}), 400
    try:
        session = stripe.billing_portal.Session.create(customer=current_user.stripe_customer_id, return_url=request.json.get("return_url", "https://recon.kryzensys.com/dashboard"))
        return jsonify({"portal_url": session.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@payments_bp.route("/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig = request.headers.get("Stripe-Signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig, stripe_webhook_secret)
    except Exception:
        return jsonify({"error": "Invalid"}), 400
    handlers = {
        "checkout.session.completed": handle_checkout_completed,
        "customer.subscription.updated": handle_subscription_updated,
        "customer.subscription.deleted": handle_subscription_deleted,
        "invoice.paid": handle_invoice_paid,
        "invoice.payment_failed": handle_payment_failed,
    }
    handler = handlers.get(event["type"])
    if handler:
        try: handler(event["data"]["object"])
        except Exception as e: logger.error(f"Webhook error: {e}")
    return jsonify({"received": True})


def handle_checkout_completed(session):
    user_id = int(session["metadata"]["user_id"])
    plan = session["metadata"]["plan"]
    user = User.query.get(user_id)
    if not user: return
    sub = Subscription.query.filter_by(user_id=user_id, status="active").first()
    if not sub:
        sub = Subscription(user_id=user_id, plan=plan.split("_")[0], status="active", stripe_subscription_id=session.get("subscription"), stripe_customer_id=session.get("customer"), started_at=datetime.utcnow(), expires_at=datetime.utcnow() + timedelta(days=30 if "monthly" in plan else 365), payment_provider="stripe", external_id=session["id"])
        db.session.add(sub)
    user.plan = plan.split("_")[0]
    db.session.commit()
    from modules.email_service import send_email, EmailTemplates
    t = EmailTemplates.welcome(user.username)
    send_email(user.email, f"🎉 Welcome to {plan.split('_')[0].title()}!", t["html"], t["text"])


def handle_subscription_updated(subscription):
    sub = Subscription.query.filter_by(stripe_subscription_id=subscription["id"]).first()
    if sub:
        sub.status = subscription["status"]
        sub.expires_at = datetime.fromtimestamp(subscription["current_period_end"])
        db.session.commit()


def handle_subscription_deleted(subscription):
    sub = Subscription.query.filter_by(stripe_subscription_id=subscription["id"]).first()
    if sub:
        sub.status = "cancelled"
        user = User.query.get(sub.user_id)
        if user: user.plan = "free"
        db.session.commit()


def handle_invoice_paid(invoice):
    user = User.query.filter_by(stripe_customer_id=invoice["customer"]).first()
    if user:
        payment = Payment(user_id=user.id, amount=invoice["amount_paid"] / 100, currency=invoice["currency"], status="succeeded", stripe_invoice_id=invoice["id"], payment_method="stripe")
        db.session.add(payment)
        inv = Invoice(user_id=user.id, invoice_number=f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{invoice['number']}", amount=invoice["amount_paid"] / 100, currency=invoice["currency"], status="paid", paid_at=datetime.utcnow())
        db.session.add(inv)
        db.session.commit()
        from modules.email_service import send_email, EmailTemplates
        t = EmailTemplates.invoice(inv.invoice_number, inv.amount, user.plan)
        send_email(user.email, t["subject"], t["html"], t["text"])


def handle_payment_failed(invoice):
    user = User.query.filter_by(stripe_customer_id=invoice["customer"]).first()
    if user:
        payment = Payment(user_id=user.id, amount=invoice["amount_due"] / 100, currency=invoice["currency"], status="failed", stripe_invoice_id=invoice["id"], payment_method="stripe")
        db.session.add(payment)
        db.session.commit()


@payments_bp.route("/subscription", methods=["GET"])
@login_required
def get_subscription():
    sub = Subscription.query.filter_by(user_id=current_user.id, status="active").first()
    if not sub: return jsonify({"plan": "free", "status": "inactive"})
    return jsonify({"plan": sub.plan, "status": sub.status, "started_at": sub.started_at, "expires_at": sub.expires_at, "days_remaining": (sub.expires_at - datetime.utcnow()).days if sub.expires_at else 0})


@payments_bp.route("/cancel", methods=["POST"])
@login_required
def cancel_subscription():
    sub = Subscription.query.filter_by(user_id=current_user.id, status="active").first()
    if not sub: return jsonify({"error": "No subscription"}), 404
    if sub.stripe_subscription_id:
        try: stripe.Subscription.delete(sub.stripe_subscription_id)
        except: pass
    sub.status = "cancelled"
    current_user.plan = "free"
    db.session.commit()
    return jsonify({"message": "Cancelled"})


@payments_bp.route("/invoices", methods=["GET"])
@login_required
def list_invoices():
    invoices = Invoice.query.filter_by(user_id=current_user.id).order_by(Invoice.created_at.desc()).limit(50).all()
    return jsonify([{"id": i.id, "number": i.invoice_number, "amount": i.amount, "currency": i.currency, "status": i.status, "created_at": i.created_at, "paid_at": i.paid_at} for i in invoices])


@payments_bp.route("/admin/payments", methods=["GET"])
@login_required
def admin_payments():
    if not current_user.is_admin: return jsonify({"error": "Admin only"}), 403
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 50)), 200)
    total = Payment.query.count()
    payments = Payment.query.order_by(Payment.created_at.desc()).limit(per_page).offset((page - 1) * per_page).all()
    return jsonify({"total": total, "page": page, "per_page": per_page, "payments": [{"id": p.id, "user_id": p.user_id, "amount": p.amount, "currency": p.currency, "status": p.status, "created_at": p.created_at} for p in payments]})
