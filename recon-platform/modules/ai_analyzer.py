"""ispeak module integration - AI-powered reconnaissance assistant"""
import os
import json
from datetime import datetime
from typing import List, Dict, Optional


class ReconAIAssistant:
    """AI assistant for reconnaissance guidance - powered by Groq"""

    @staticmethod
    def suggest_next_steps(scan_data: dict, language: str = "en") -> str:
        """Suggest next recon steps based on findings"""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return "Configure GROQ_API_KEY for AI suggestions."
        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            prompt = f"""Based on these reconnaissance findings, suggest the next 5 steps to deepen the security assessment:

Target: {scan_data.get('target')}
Risk Score: {scan_data.get('risk_score', 0)}/100
Open Ports: {len(scan_data.get('open_ports', []))}
Subdomains Found: {len(scan_data.get('subdomains', []))}
Technologies: {scan_data.get('technologies', [])}
Vulnerabilities: {len(scan_data.get('vulnerabilities', []))}

Provide actionable next steps in {language} language with priority order and estimated time."""
            chat = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a senior penetration tester. Provide concise, actionable recon guidance."},
                    {"role": "user", "content": prompt},
                ],
                model="llama-3.3-70b-versatile", temperature=0.3, max_tokens=1024,
            )
            return chat.choices[0].message.content
        except Exception as e:
            return f"AI unavailable: {e}"

    @staticmethod
    def analyze_tech_stack(technologies: List[str], target: str) -> Dict:
        """Analyze detected technologies for known vulnerabilities"""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return {"error": "GROQ_API_KEY not set"}
        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            prompt = f"""Analyze this technology stack for security risks:

Target: {target}
Technologies: {', '.join(technologies)}

Return JSON: {{"technologies": [{{"name": "...", "risks": [...], "recommendations": [...]}}]}}"""
            chat = client.chat.completions.create(
                messages=[{"role": "system", "content": "Security analyst. JSON only."}, {"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile", temperature=0.2, max_tokens=2048,
                response_format={"type": "json_object"},
            )
            return json.loads(chat.choices[0].message.content)
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def correlate_findings(findings: List[Dict]) -> str:
        """Find attack chain possibilities"""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return "Configure GROQ_API_KEY for AI analysis."
        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            findings_text = "\n".join([f"- [{f.get('severity', 'unknown')}] {f.get('title', '')}" for f in findings[:20]])
            prompt = f"""Analyze security findings and identify attack chains:

{findings_text}

Identify:
1. Which findings could be combined
2. Attack chain scenarios
3. Most critical path
4. Remediation priority"""
            chat = client.chat.completions.create(
                messages=[{"role": "system", "content": "Offensive security expert."}, {"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile", temperature=0.4, max_tokens=2048,
            )
            return chat.choices[0].message.content
        except Exception as e:
            return f"AI unavailable: {e}"

    @staticmethod
    def generate_poc(vulnerability: Dict) -> str:
        """Generate safe educational PoC"""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return "Configure GROQ_API_KEY for PoC generation."
        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            prompt = f"""Generate a SAFE, EDUCATIONAL proof-of-concept for verification only. No destructive actions.

Vulnerability: {vulnerability.get('title')}
Description: {vulnerability.get('description')}
Severity: {vulnerability.get('severity')}

Generate Python or curl-based safe PoC."""
            chat = client.chat.completions.create(
                messages=[{"role": "system", "content": "Security educator. Safe defensive PoCs only."}, {"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile", temperature=0.3, max_tokens=2048,
            )
            return chat.choices[0].message.content
        except Exception as e:
            return f"AI unavailable: {e}"

    @staticmethod
    def chat(message: str, history: List[Dict] = None) -> str:
        """Interactive chat for security questions"""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return "Configure GROQ_API_KEY for AI chat."
        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            messages = [{"role": "system", "content": "You are a professional cybersecurity assistant for Recon Platform. Help with web security testing, network recon, vulnerability analysis. Always emphasize authorized testing only."}]
            if history:
                messages.extend(history[-10:])
            messages.append({"role": "user", "content": message})
            chat = client.chat.completions.create(messages=messages, model="llama-3.3-70b-versatile", temperature=0.5, max_tokens=2048)
            return chat.choices[0].message.content
        except Exception as e:
            return f"AI unavailable: {e}"


# Original ispeak preserved
class IspeakChat:
    """Original AI chat from ispeak module - now integrated"""
    @staticmethod
    def process_message(message: str, user_context: dict = None) -> str:
        return ReconAIAssistant.chat(message, user_context.get("history") if user_context else None)


def integrate_with_ispeak():
    """Migration helper - imports old ispeak functionality"""
    try:
        from ispeak.services.groq_service import GroqService
        return GroqService
    except ImportError:
        return ReconAIAssistant
