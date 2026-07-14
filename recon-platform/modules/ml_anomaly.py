"""ML-based anomaly detection for scan results"""
import os
import json
import pickle
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from models import db, Scan, Finding, User, ActivityLog

logger = logging.getLogger(__name__)

class AnomalyDetector:
    """Detects anomalies in scan results and user behavior"""
    def __init__(self):
        self.iso_forest = IsolationForest(contamination=0.1, random_state=42, n_estimators=100)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_path = os.getenv("ML_MODEL_PATH", "/app/models/anomaly.pkl")
        self._load_or_init()

    def _load_or_init(self):
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, "rb") as f:
                    data = pickle.load(f)
                    self.iso_forest = data.get("model", self.iso_forest)
                    self.scaler = data.get("scaler", self.scaler)
                    self.is_trained = data.get("trained", False)
                    logger.info("✅ ML model loaded")
        except Exception as e:
            logger.warning(f"ML model load failed: {e}")

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, "wb") as f:
                pickle.dump({"model": self.iso_forest, "scaler": self.scaler, "trained": self.is_trained}, f)
        except Exception as e:
            logger.error(f"ML model save failed: {e}")

    def extract_features(self, scan: Scan, findings: List[Finding]) -> List[float]:
        """Extract numerical features from a scan"""
        severities = [f.severity for f in findings]
        severity_counts = [severities.count(i) for i in range(5)]
        return [
            len(findings),
            sum(severity_counts[3:]),
            sum(severity_counts[:2]),
            scan.duration or 0,
            len(set(f.category for f in findings)),
            np.mean([len(f.description or "") for f in findings]) if findings else 0,
            scan.target.count('.'),
            1 if scan.scan_type and 'full' in scan.scan_type else 0,
            len(set(f.url.split('/')[2] for f in findings if f.url and '://' in f.url)),
        ]

    def train(self, scans_data: List[Tuple[Scan, List[Finding]]] = None):
        """Train on historical data"""
        if not scans_data:
            scans_data = self._load_historical_data()
        if len(scans_data) < 10:
            logger.warning(f"Insufficient data for training: {len(scans_data)} samples")
            return False
        X = np.array([self.extract_features(s, f) for s, f in scans_data])
        X_scaled = self.scaler.fit_transform(X)
        self.iso_forest.fit(X_scaled)
        self.is_trained = True
        self._save()
        logger.info(f"✅ ML model trained on {len(scans_data)} samples")
        return True

    def _load_historical_data(self) -> List[Tuple[Scan, List[Finding]]]:
        data = []
        for scan in Scan.query.limit(1000).all():
            findings = Finding.query.filter_by(scan_id=scan.id).all()
            data.append((scan, findings))
        return data

    def detect_scan_anomaly(self, scan: Scan, findings: List[Finding]) -> Dict:
        """Detect if scan results are anomalous"""
        if not self.is_trained:
            return {"is_anomaly": False, "score": 0, "reason": "Model not trained yet"}
        try:
            features = np.array([self.extract_features(scan, findings)])
            features_scaled = self.scaler.transform(features)
            prediction = self.iso_forest.predict(features_scaled)[0]
            score = self.iso_forest.score_samples(features_scaled)[0]
            is_anomaly = prediction == -1
            return {
                "is_anomaly": is_anomaly,
                "score": float(score),
                "severity": "high" if score < -0.5 else "medium" if score < -0.2 else "low",
                "reasons": self._explain_anomaly(scan, findings, is_anomaly),
            }
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return {"is_anomaly": False, "error": str(e)}

    def _explain_anomaly(self, scan: Scan, findings: List[Finding], is_anomaly: bool) -> List[str]:
        if not is_anomaly: return []
        reasons = []
        severities = [f.severity for f in findings]
        high = sum(1 for s in severities if s >= 3)
        if high > 10: reasons.append(f"Unusually high number of critical findings: {high}")
        if len(findings) > 100: reasons.append(f"Abnormal finding count: {len(findings)}")
        if scan.duration and scan.duration > 600: reasons.append(f"Long scan duration: {scan.duration}s")
        return reasons if reasons else ["Statistical outlier from normal scan patterns"]

    def detect_user_behavior_anomaly(self, user_id: int) -> Dict:
        """Detect unusual user activity patterns"""
        recent = ActivityLog.query.filter(
            ActivityLog.user_id == user_id,
            ActivityLog.created_at >= datetime.utcnow() - timedelta(days=7)
        ).all()
        if not recent: return {"is_anomaly": False}
        hourly = defaultdict(int)
        daily = defaultdict(int)
        ip_counts = defaultdict(int)
        for log in recent:
            hourly[log.created_at.hour] += 1
            daily[log.created_at.date().isoformat()] += 1
            if log.ip_address: ip_counts[log.ip_address] += 1
        suspicious = []
        if len(ip_counts) > 5: suspicious.append(f"Activity from {len(ip_counts)} different IPs in 7 days")
        max_daily = max(daily.values()) if daily else 0
        if max_daily > 100: suspicious.append(f"Unusually high activity: {max_daily} actions in single day")
        return {"is_anomaly": len(suspicious) > 0, "suspicious_indicators": suspicious, "activity_count": len(recent)}

    def get_severity_prediction(self, scan_features: Dict) -> Dict:
        """Predict likely severity level of a scan based on target info"""
        target_len = len(scan_features.get("target", ""))
        has_subdomains = scan_features.get("has_subdomains", False)
        if has_subdomains: return {"predicted_severity": "high", "confidence": 0.75, "reason": "Multiple subdomains increase attack surface"}
        if target_len > 30: return {"predicted_severity": "medium", "confidence": 0.6, "reason": "Long URLs often hide parameters"}
        return {"predicted_severity": "low", "confidence": 0.5, "reason": "Simple target"}

_detector = None
def get_anomaly_detector() -> AnomalyDetector:
    global _detector
    if _detector is None: _detector = AnomalyDetector()
    return _detector
