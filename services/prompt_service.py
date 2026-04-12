from openai import OpenAI


class PromptGenerator:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def generate(self, mode: str, task_name: str, user_text: str, level: str | None = None) -> str:
        clean_text = user_text.strip()

        base_instructions = (
            "You are an expert prompt engineer. "
            "Write exactly one high-quality prompt that the user can copy and paste into ChatGPT or a similar AI tool. "
            "The prompt must be clear, specific, natural, and designed to produce a useful response. "
            "Include enough context, a clear goal, and output guidance when helpful. "
            "Whenever useful, write the prompt so it naturally includes: the role the AI should play, the user's goal, "
            "the provided content, and the desired output format. "
            "The final prompt should feel polished, practical, and ready to use. "
            "Return only the final prompt."
        )

        student_task_guides = {
            "Explain a topic": (
                "Create a prompt that asks the AI to explain the topic clearly at the student's level. "
                "Encourage simple language, step-by-step teaching, key ideas, and examples."
            ),
            "Summarize notes": (
                "Create a prompt that asks the AI to turn the notes into an organized study summary. "
                "Encourage headings, bullet points, key concepts, and quick review points."
            ),
            "Make quiz questions": (
                "Create a prompt that asks the AI to generate helpful practice questions based on the topic or notes. "
                "Encourage a clear set of questions and an answer key."
            ),
            "Improve writing": (
                "Create a prompt that asks the AI to improve the writing for clarity, grammar, organization, and flow "
                "while preserving the student's original meaning."
            ),
        }

        research_task_guides = {
            "Summarize a paper": (
                "Create a prompt that asks the AI to summarize the paper in a structured academic way. "
                "Encourage coverage of purpose, methods, main findings, limitations, and significance."
            ),
            "Improve academic writing": (
                "Create a prompt that asks the AI to improve academic writing for clarity, coherence, formality, grammar, "
                "and stronger academic tone while preserving the original meaning."
            ),
            "Generate research questions": (
                "Create a prompt that asks the AI to generate focused, researchable, academically rigorous research questions. "
                "Encourage clarity, relevance, and suitability for academic study."
            ),
        }

        if mode == "Student":
            task_guide = student_task_guides.get(task_name, "Create a helpful learning-focused prompt.")
            user_input = f"""
Mode: Student
Task: {task_name}
Student level: {level}
User content:
{clean_text}

Task-specific goal:
{task_guide}

Requirements for the generated prompt:
- support learning, understanding, practice, or writing improvement
- match the student's level
- be clear and easy to copy and use
- avoid encouraging cheating or dishonest work

Return only the final prompt.
"""
        else:
            task_guide = research_task_guides.get(task_name, "Create a helpful academic prompt.")
            user_input = f"""
Mode: Research
Task: {task_name}
User content:
{clean_text}

Task-specific goal:
{task_guide}

Requirements for the generated prompt:
- be academically useful
- be clear, specific, and well-structured
- support summarization, analysis, writing improvement, or question generation
- sound professional and ready to use

Return only the final prompt.
"""

        response = self.client.responses.create(
            model="gpt-5.4",
            instructions=base_instructions,
            input=user_input,
        )
        return response.output_text.strip()
