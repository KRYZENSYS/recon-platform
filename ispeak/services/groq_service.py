"""Groq AI xizmati — chatbot va talaffuz uchun."""
import base64
import json
import re
from typing import List, Dict, Optional

from groq import Groq
from config import Config


class GroqService:
    """Groq API bilan ishlash uchun asosiy klass."""

    def __init__(self):
        self.client = Groq(api_key=Config.GROQ_API_KEY)
        self.chat_model = Config.GROQ_CHAT_MODEL
        self.whisper_model = Config.GROQ_WHISPER_MODEL

    # =========================================
    # AI CHATBOT
    # =========================================

    def get_chat_response(
        self,
        user_message: str,
        scenario: str,
        language: str,
        user_level: str,
        history: List[Dict] = None,
        native_language: str = 'uz'
    ) -> Dict:
        """AI chatbotdan javob olish + xatolarni tuzatish.

        Returns:
            {
                'reply': str,
                'corrections': List[Dict],
                'translation': str,
                'suggestions': List[str]
            }
        """
        history = history or []

        system_prompt = self._build_chat_system_prompt(
            scenario, language, user_level, native_language
        )

        messages = [{'role': 'system', 'content': system_prompt}]
        for msg in history[-10:]:
            messages.append(msg)
        messages.append({'role': 'user', 'content': user_message})

        try:
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                temperature=0.7,
                max_tokens=600,
                response_format={'type': 'json_object'}
            )

            content = response.choices[0].message.content
            return self._parse_chat_response(content)

        except Exception as e:
            return {
                'reply': f'Kechirasiz, xatolik yuz berdi: {str(e)[:100]}',
                'corrections': [],
                'translation': '',
                'suggestions': []
            }

    def _build_chat_system_prompt(self, scenario, language, level, native):
        """Chatbot uchun system prompt yaratish."""
        lang_name = Config.SUPPORTED_LANGUAGES.get(language, language)
        native_name = Config.SUPPORTED_LANGUAGES.get(native, native)

        scenario_descriptions = {
            'restaurant': 'restoranda ovqat buyurtma qilish',
            'airport': 'aeroportda ro\'yxatdan o\'tish va savol berish',
            'hotel': 'mehmaxonada xona bron qilish',
            'shopping': 'do\'konda narsa sotib olish',
            'job_interview': 'ish suhbatida ishtirok etish',
            'doctor': 'shifokorga tashrif va simptomlar tasvir',
            'directions': 'yo\'l so\'rash va ko\'rsatmalar berish',
            'small_talk': 'kundalik suhbat va salomlashish',
            'business_meeting': 'biznes uchrashuvda qatnashish',
            'phone_call': 'telefonda suhbat qilish',
        }

        scenario_text = scenario_descriptions.get(scenario, scenario)

        return f"""You are iSpeak, a friendly language learning assistant. The user is learning {lang_name} at {level} level. Their native language is {native_name}.

SCENARIO: {scenario_text}

Your task:
1. Respond naturally in {lang_name} as a native speaker would in this scenario
2. Keep your reply SHORT (max 2-3 sentences)
3. If the user makes grammar or spelling mistakes, gently correct them
4. After your reply, provide a translation in {native_name}
5. Suggest 2-3 follow-up phrases the user could say

IMPORTANT: Return ONLY valid JSON in this exact format:
{{
    "reply": "Your response in {lang_name}",
    "corrections": [
        {{"wrong": "user's wrong text", "correct": "correct version", "explanation": "brief explanation in {native_name}"}}
    ],
    "translation": "Translation of your reply in {native_name}",
    "suggestions": ["suggestion 1 in {lang_name}", "suggestion 2", "suggestion 3"]
}}

If the user wrote correctly, return an empty corrections array.
Make the conversation engaging and educational.
"""

    def _parse_chat_response(self, content: str) -> Dict:
        """AI javobini parse qilish."""
        try:
            data = json.loads(content)
            return {
                'reply': data.get('reply', ''),
                'corrections': data.get('corrections', []),
                'translation': data.get('translation', ''),
                'suggestions': data.get('suggestions', [])
            }
        except json.JSONDecodeError:
            # JSON bo'lmasa, matn sifatida qaytarish
            return {
                'reply': content,
                'corrections': [],
                'translation': '',
                'suggestions': []
            }

    # =========================================
    # TALAFUZLASH (Whisper)
    # =========================================

    def transcribe_audio(self, audio_file_path: str, language: str = None) -> str:
        """Audio faylni matnga aylantirish (Whisper)."""
        try:
            with open(audio_file_path, 'rb') as audio_file:
                params = {'file': audio_file, 'model': self.whisper_model}
                if language:
                    params['language'] = language

                transcription = self.client.audio.transcriptions.create(**params)
                return transcription.text
        except Exception as e:
            raise Exception(f'Transcription failed: {str(e)}')

    def evaluate_pronunciation(
        self,
        expected_text: str,
        recognized_text: str,
        language: str,
        native_language: str = 'uz'
    ) -> Dict:
        """Talaffuzni baholash va feedback berish.

        Returns:
            {
                'accuracy': int (0-100),
                'feedback': str,
                'word_comparison': List[Dict]
            }
        """
        # So'z bo'yicha taqqoslash
        expected_words = expected_text.lower().split()
        recognized_words = recognized_text.lower().split() if recognized_text else []

        comparison = []
        correct_count = 0
        max_len = max(len(expected_words), len(recognized_words))

        for i in range(max_len):
            exp = expected_words[i] if i < len(expected_words) else None
            rec = recognized_words[i] if i < len(recognized_words) else None
            match = exp == rec
            if match and exp:
                correct_count += 1
            comparison.append({
                'expected': exp or '',
                'recognized': rec or '',
                'correct': match
            })

        accuracy = int((correct_count / len(expected_words)) * 100) if expected_words else 0

        # AI dan batafsil feedback olish
        native_name = Config.SUPPORTED_LANGUAGES.get(native_language, native_language)
        lang_name = Config.SUPPORTED_LANGUAGE_SUPPORTED_LANGUAGES.get(language, language) if hasattr(Config, 'LANGUAGE_SUPPORTED_LANGUAGES') else language

        feedback_prompt = f"""You are a pronunciation coach. The user tried to say: "{expected_text}"
They actually said: "{recognized_text}"
Accuracy: {accuracy}%

Give a SHORT encouraging feedback in {native_name} (1-2 sentences) with specific tips on which words to focus on. Be supportive and constructive."""

        try:
            feedback_response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[{'role': 'user', 'content': feedback_prompt}],
                max_tokens=200,
                temperature=0.7
            )
            feedback = feedback_response.choices[0].message.content
        except Exception:
            if accuracy >= 90:
                feedback = "Ajoyib talaffuz! 🌟"
            elif accuracy >= 70:
                feedback = "Yaxshi! Biroz mashq qiling. 💪"
            elif accuracy >= 50:
                feedback = "Yomon emas, lekin yana urinib ko'ring. 📚"
            else:
                feedback = "Iborani tinglab, qaytadan urinib ko'ring. 🎧"

        return {
            'accuracy': accuracy,
            'feedback': feedback,
            'word_comparison': comparison,
            'expected_text': expected_text,
            'recognized_text': recognized_text,
        }

    # =========================================
    # DARSLAR YARATISH
    # =========================================

    def generate_lesson_content(self, language: str, level: str, topic: str) -> Dict:
        """AI yordamida yangi dars kontenti yaratish."""
        lang_name = Config.SUPPORTED_LANGUAGES.get(language, language)

        prompt = f"""Create a {level} level {lang_name} lesson about "{topic}".

Return JSON:
{{
    "title": "Lesson title in {lang_name}",
    "description": "Short description",
    "vocabulary": [
        {{"word": "...", "translation": "...", "example": "..."}}
    ],
    "dialogue": [
        {{"speaker": "A", "text": "..."}},
        {{"speaker": "B", "text": "..."}}
    ],
    "grammar_tip": "Brief grammar explanation",
    "quiz": [
        {{"question": "...", "options": ["A", "B", "C"], "correct": 0}}
    ]
}}

Include 8-10 vocabulary words, 6-8 dialogue lines, and 3-4 quiz questions."""

        try:
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.8,
                max_tokens=2000,
                response_format={'type': 'json_object'}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            raise Exception(f'Lesson generation failed: {str(e)}')

    # =========================================
    # IBORALAR GENERATSIYASI
    # =========================================

    def generate_practice_phrases(self, language: str, level: str, count: int = 5) -> List[str]:
        """Talaffuz mashqi uchun iboralar yaratish."""
        lang_name = Config.SUPPORTED_LANGUAGES.get(language, language)

        prompt = f"Generate {count} short {level} level phrases in {lang_name} for pronunciation practice. Return ONLY a JSON array of strings, no explanations."

        try:
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.9,
                max_tokens=300,
                response_format={'type': 'json_object'}
            )
            data = json.loads(response.choices[0].message.content)
            # JSON array qaytarilishi kerak
            if isinstance(data, list):
                return data
            return data.get('phrases', [])
        except Exception:
            return [
                'Hello, how are you?',
                'Nice to meet you.',
                'Where are you from?',
                'What do you do?',
                'Have a nice day!'
            ]


# Singleton
groq_service = GroqService()