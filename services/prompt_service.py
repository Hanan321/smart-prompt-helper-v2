from openai import OpenAI


class PromptGenerator:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def generate(self, audience: str, task_name: str, user_text: str, level: str | None = None) -> str:
        clean_text = user_text.strip()

        base_instructions = (
            "You are an expert prompt engineer specializing in academic and research workflows. "
            "Write exactly one high-quality prompt that the user can copy and paste into ChatGPT or a similar AI tool. "
            "The prompt must be clear, precise, professional, and designed to produce a strong academic-quality response. "
            "Include clear context, a defined goal, and specific output instructions. "
            "Whenever appropriate, structure the prompt so the AI understands: its role, the task, the input content, "
            "and the expected output format. "
            "The final prompt should be polished, practical, and ready for academic or professional use. "
            "Return only the final prompt."
        )

        academic_task_guides = {
            "Summarize a research paper": (
                "Create a prompt that asks the AI to summarize the paper in a structured academic format. "
                "Encourage sections such as: objective, methodology, key findings, limitations, and significance."
            ),
            "Improve academic writing": (
                "Create a prompt that asks the AI to refine academic writing for clarity, coherence, grammar, "
                "formality, and stronger academic tone while preserving the original meaning."
            ),
            "Generate research questions": (
                "Create a prompt that asks the AI to generate clear, focused, and researchable academic questions. "
                "Encourage depth, relevance, and suitability for scholarly work."
            ),
            "Refine a literature review": (
                "Create a prompt that asks the AI to improve the structure, flow, and synthesis of a literature review. "
                "Encourage linking ideas, improving transitions, and highlighting key themes."
            ),
            "Turn notes into a structured academic outline": (
                "Create a prompt that asks the AI to organize the notes into a clear academic outline. "
                "Encourage logical structure, headings, subheadings, and coherent flow."
            ),
            "Rewrite for clarity, formality, and precision": (
                "Create a prompt that asks the AI to rewrite the content with improved clarity, precision, and formal tone. "
                "Ensure the meaning is preserved while improving readability and professionalism."
            ),
        }

        task_guide = academic_task_guides.get(
            task_name,
            "Create a high-quality academic prompt that improves clarity, structure, and usefulness."
        )

        user_input = f"""
Audience: {audience}
Task: {task_name}

User content:
{clean_text}

Task-specific goal:
{task_guide}

Requirements for the generated prompt:
- be suitable for academic, research, or professional use
- be clear, specific, and well-structured
- guide the AI to produce high-quality, organized output
- encourage structured responses when appropriate (headings, bullet points, sections)
- maintain academic tone and clarity

Return only the final prompt.
"""

        response = self.client.responses.create(
            model="gpt-5.4",
            instructions=base_instructions,
            input=user_input,
        )

        return response.output_text.strip()