from openai import OpenAI


class PromptGenerator:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Missing OpenAI API key.")
        self.client = OpenAI(api_key=api_key)

    def generate(self, audience: str, task_name: str, user_text: str) -> str:
        clean_text = user_text.strip()

        base_instructions = (
            "You are an expert prompt engineer. "
            "Write exactly one high-quality prompt that the user can copy and paste into ChatGPT or a similar AI tool. "
            "The prompt must be clear, specific, natural, and designed to produce a useful response. "
            "Include enough context, a clear goal, and output guidance when helpful. "
            "Whenever useful, write the prompt so it naturally includes the AI role, the user's goal, "
            "the provided content, and the desired output format. "
            "Adapt the prompt quality, complexity, tone, and structure to match the selected audience. "
            "Return only the final prompt."
        )

        audience_guides = {
            "Undergraduate": (
                "The generated prompt should ask for a response that is clear, supportive, easy to follow, and educational. "
                "Prefer plain language, step-by-step explanation when useful, and practical structure."
            ),
            "Graduate": (
                "The generated prompt should ask for a response that is academically strong, well-structured, and appropriately detailed. "
                "Encourage analytical depth, organization, and formal academic tone."
            ),
            "Researcher / Professional": (
                "The generated prompt should ask for a response that is rigorous, precise, formal, and suitable for advanced academic or professional research use. "
                "Encourage synthesis, nuance, discipline-appropriate terminology, and strong structural clarity."
            ),
        }

        task_guides = {
            "Explain a topic": (
                "Create a prompt that asks the AI to explain the topic clearly and accurately with key concepts and examples."
            ),
            "Summarize notes": (
                "Create a prompt that asks the AI to turn the notes into an organized summary with headings, key takeaways, and study-friendly structure."
            ),
            "Make quiz questions": (
                "Create a prompt that asks the AI to generate useful quiz or practice questions from the content, with an answer key."
            ),
            "Improve writing": (
                "Create a prompt that asks the AI to improve the writing for clarity, grammar, flow, and organization while preserving meaning."
            ),
            "Summarize a research paper": (
                "Create a prompt that asks the AI to summarize the paper in a structured academic format including objective, methodology, findings, limitations, and significance."
            ),
            "Improve academic writing": (
                "Create a prompt that asks the AI to refine academic writing for clarity, coherence, grammar, formality, and stronger academic tone."
            ),
            "Generate research questions": (
                "Create a prompt that asks the AI to generate clear, focused, and researchable academic questions suitable for scholarly work."
            ),
            "Refine a literature review": (
                "Create a prompt that asks the AI to improve the structure, flow, and synthesis of a literature review."
            ),
            "Turn notes into a structured academic outline": (
                "Create a prompt that asks the AI to organize the notes into a clear outline with headings and subheadings."
            ),
            "Rewrite for clarity, formality, and precision": (
                "Create a prompt that asks the AI to rewrite the content with improved clarity, precision, and formal tone while preserving meaning."
            ),
        }

        audience_guide = audience_guides.get(
            audience,
            "The generated prompt should be clear, well-structured, and suitable for academic or professional use.",
        )

        task_guide = task_guides.get(
            task_name,
            "Create a high-quality prompt that improves clarity, structure, and usefulness.",
        )

        user_input = f"""
Audience: {audience}
Task: {task_name}

User content:
{clean_text}

Audience-specific guidance:
{audience_guide}

Task-specific goal:
{task_guide}

Requirements:
- be clear, specific, and easy to use
- match the audience level and expected quality
- guide the AI to produce a strong, organized response
- encourage structured output when useful
- preserve academic honesty
- sound polished and ready to paste into an AI tool

Return only the final prompt.
"""

        try:
            response = self.client.responses.create(
                model="gpt-5.4",
                instructions=base_instructions,
                input=user_input,
            )
            return response.output_text.strip()
        except Exception as exc:
            raise RuntimeError(f"Prompt generation failed: {exc}") from exc