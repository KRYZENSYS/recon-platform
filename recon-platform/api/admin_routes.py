"""Lab API - 100+ functions exposed via REST"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from modules.lab_functions import LAB_FUNCTIONS, function_101_color_contrast, function_102_exif_strip

lab_bp = Blueprint("lab", __name__, url_prefix="/api/v1/lab")


def safe_run(func, *args, **kwargs):
    """Run function with error handling"""
    try:
        result = func(*args, **kwargs)
        if not isinstance(result, (dict, list, str, int, float, bool, type(None))):
            result = str(result)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@lab_bp.route("/functions", methods=["GET"])
@login_required
def list_functions():
    """List all 100+ lab functions"""
    funcs = []
    for fname, func in LAB_FUNCTIONS.items():
        try:
            import inspect
            sig = inspect.signature(func)
            params = [{"name": p.name, "default": p.default if p.default != p.empty else None, "type": str(p.annotation) if p.annotation != p.empty else "any"} for p in sig.parameters.values()]
        except:
            params = []
        funcs.append({"id": fname, "name": fname.replace("_", " ").title(), "params": params, "category": _get_category(fname)})
    return jsonify({"total": len(funcs), "functions": funcs, "categories": list(set(_get_category(f) for f in LAB_FUNCTIONS))})


def _get_category(fname):
    num = int(fname.split("_")[1])
    if 1 <= num <= 10: return "Encoding"
    if 11 <= num <= 20: return "Hashing"
    if 21 <= num <= 30: return "Network"
    if 31 <= num <= 40: return "Crypto"
    if 41 <= num <= 50: return "OSINT"
    if 51 <= num <= 60: return "Web Security"
    if 61 <= num <= 70: return "Network Scanning"
    if 71 <= num <= 80: return "Text Analysis"
    if 81 <= num <= 90: return "Utilities"
    if 91 <= num <= 100: return "Advanced Security"
    return "Other"


@lab_bp.route("/exec/<func_id>", methods=["POST"])
@login_required
def execute_function(func_id):
    """Execute lab function by ID"""
    if func_id not in LAB_FUNCTIONS:
        return jsonify({"error": "Function not found"}), 404
    data = request.json or {}
    func = LAB_FUNCTIONS[func_id]
    import inspect
    try:
        sig = inspect.signature(func)
        args = {}
        for p in sig.parameters.values():
            if p.name in data:
                args[p.name] = data[p.name]
        return safe_run(func, **args)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@lab_bp.route("/category/<category>", methods=["GET"])
@login_required
def by_category(category):
    """Get functions by category"""
    funcs = [(k, v) for k, v in LAB_FUNCTIONS.items() if _get_category(k).lower() == category.lower()]
    return jsonify({"category": category, "count": len(funcs), "functions": [{"id": k, "name": k.replace("_", " ").title()} for k, v in funcs]})


# Specific endpoints for common functions
@lab_bp.route("/base64/encode", methods=["POST"])
@login_required
def base64_encode(): return safe_run(LAB_FUNCTIONS["function_01_base64_encode"], request.json.get("text", ""))

@lab_bp.route("/base64/decode", methods=["POST"])
@login_required
def base64_decode(): return safe_run(LAB_FUNCTIONS["function_02_base64_decode"], request.json.get("text", ""))

@lab_bp.route("/url/encode", methods=["POST"])
@login_required
def url_encode(): return safe_run(LAB_FUNCTIONS["function_03_url_encode"], request.json.get("text", ""))

@lab_bp.route("/url/decode", methods=["POST"])
@login_required
def url_decode(): return safe_run(LAB_FUNCTIONS["function_04_url_decode"], request.json.get("text", ""))

@lab_bp.route("/hash/md5", methods=["POST"])
@login_required
def hash_md5(): return safe_run(LAB_FUNCTIONS["function_11_md5"], request.json.get("text", ""))

@lab_bp.route("/hash/sha1", methods=["POST"])
@login_required
def hash_sha1(): return safe_run(LAB_FUNCTIONS["function_12_sha1"], request.json.get("text", ""))

@lab_bp.route("/hash/sha256", methods=["POST"])
@login_required
def hash_sha256(): return safe_run(LAB_FUNCTIONS["function_13_sha256"], request.json.get("text", ""))

@lab_bp.route("/hash/sha512", methods=["POST"])
@login_required
def hash_sha512(): return safe_run(LAB_FUNCTIONS["function_14_sha512"], request.json.get("text", ""))

@lab_bp.route("/dns/lookup", methods=["POST"])
@login_required
def dns_lookup(): return safe_run(LAB_FUNCTIONS["function_21_dns_lookup"], request.json.get("domain", ""))

@lab_bp.route("/whois", methods=["POST"])
@login_required
def whois(): return safe_run(LAB_FUNCTIONS["function_23_whois"], request.json.get("domain", ""))

@lab_bp.route("/headers/check", methods=["POST"])
@login_required
def headers_check(): return safe_run(LAB_FUNCTIONS["function_27_security_headers_check"], request.json.get("url", ""))

@lab_bp.route("/port/scan", methods=["POST"])
@login_required
def port_scan(): return safe_run(LAB_FUNCTIONS["function_68_tcp_syn_scan_sim"], request.json.get("host", ""), request.json.get("ports"))

@lab_bp.route("/subdomain/find", methods=["POST"])
@login_required
def subdomain_find(): return safe_run(LAB_FUNCTIONS["function_41_subdomain_enum"], request.json.get("domain", ""))

@lab_bp.route("/email/harvest", methods=["POST"])
@login_required
def email_harvest(): return safe_run(LAB_FUNCTIONS["function_42_email_harvest"], request.json.get("domain", ""))

@lab_bp.route("/password/strength", methods=["POST"])
@login_required
def password_strength(): return safe_run(LAB_FUNCTIONS["function_39_password_strength"], request.json.get("password", ""))

@lab_bp.route("/password/generate", methods=["POST"])
@login_required
def password_generate():
    data = request.json or {}
    return safe_run(LAB_FUNCTIONS["function_40_password_generate"], data.get("length", 16), data.get("special", True))

@lab_bp.route("/jwt/decode", methods=["POST"])
@login_required
def jwt_decode(): return safe_run(LAB_FUNCTIONS["function_19_jwt_decode"], request.json.get("token", ""))

@lab_bp.route("/jwt/weak", methods=["POST"])
@login_required
def jwt_weak(): return safe_run(LAB_FUNCTIONS["function_20_jwt_weak_secret_check"], request.json.get("token", ""))

@lab_bp.route("/uuid", methods=["POST"])
@login_required
def uuid_gen(): return safe_run(LAB_FUNCTIONS["function_81_uuid_generate"], request.json.get("version", 4))

@lab_bp.route("/qr", methods=["POST"])
@login_required
def qr_gen(): return safe_run(LAB_FUNCTIONS["function_82_qr_generate"], request.json.get("data", ""))

@lab_bp.route("/totp", methods=["POST"])
@login_required
def totp_gen(): return safe_run(LAB_FUNCTIONS["function_92_2fa_totp"], request.json.get("secret", ""))

@lab_bp.route("/iptest", methods=["POST"])
@login_required
def iptest(): return safe_run(LAB_FUNCTIONS["function_64_ip_validator"], request.json.get("ip", ""))

@lab_bp.route("/ssl/info", methods=["POST"])
@login_required
def ssl_info(): return safe_run(LAB_FUNCTIONS["function_25_ssl_info"], request.json.get("host", ""), request.json.get("port", 443))

@lab_bp.route("/xss/payloads", methods=["GET"])
@login_required
def xss_payloads(): return safe_run(LAB_FUNCTIONS["function_48_xss_payloads"])

@lab_bp.route("/sqli/payloads", methods=["GET"])
@login_required
def sqli_payloads(): return safe_run(LAB_FUNCTIONS["function_49_sql_injection_payloads"])

@lab_bp.route("/ssrf/payloads", methods=["GET"])
@login_required
def ssrf_payloads(): return safe_run(LAB_FUNCTIONS["function_50_ssrf_payloads"])

@lab_bp.route("/cve", methods=["POST"])
@login_required
def cve(): return safe_run(LAB_FUNCTIONS["function_98_cve_lookup"], request.json.get("keyword", ""))

@lab_bp.route("/ioc/extract", methods=["POST"])
@login_required
def ioc_extract(): return safe_run(LAB_FUNCTIONS["function_96_ioc_extractor"], request.json.get("text", ""))

@lab_bp.route("/stix", methods=["POST"])
@login_required
def stix_create(): return safe_run(LAB_FUNCTIONS["function_97_stix_bundle_create"], request.json.get("iocs", {}))

@lab_bp.route("/color/contrast", methods=["POST"])
@login_required
def color_contrast():
    data = request.json
    return safe_run(function_101_color_contrast, tuple(data.get("rgb1", [0,0,0])), tuple(data.get("rgb2", [255,255,255])))
