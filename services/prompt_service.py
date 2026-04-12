from openai import OpenAI


class PromptGenerator:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def generate(self, audience: str, task_name: str, user_text: str, level: str | None = None) -> str:
        clean_text = user_text.strip()

        base_instructions = (
            "You are an expert prompt engineer. "
            "Write exactly one high-quality prompt that the user can copy and paste into ChatGPT or a similar AI tool. "
            "The prompt must be clear, specific, natural, and designed to produce a useful response. "
            "Include enough context, a clear goal, and output guidance when helpful. "
            "Whenever useful, write the prompt so it naturally includes: the role the AI should play, the user's goal, "
            "the provided content, and the desired output format. "
            "Adapt the prompt quality, complexity, tone, and structure to match the selected audience. "
            "Return only the final prompt."
        )

        audience_guides = {
            "Undergraduate": (
                "The generated prompt should ask for a response that is clear, supportive, easy to follow, and educational. "
                "Prefer plain language, step-by-step explanation when useful, and practical structure. "
                "The tone should still be academically appropriate, but not overly technical unless the input clearly requires it."
            ),
            "Graduate": (
                "The generated prompt should ask for a response that is academically strong, well-structured, and appropriately detailed. "
                "Encourage analytical depth, stronger organization, and more formal academic tone. "
                "The output should be useful for graduate-level coursework, seminar writing, and early research work."
            ),
            "Researcher / Professional": (
                "The generated prompt should ask for a response that is rigorous, precise, formal, and suitable for advanced academic or professional research use. "
                "Encourage synthesis, nuance, discipline-appropriate terminology, and strong structural clarity. "
                "The output should feel suitable for scholarly analysis, manuscript development, research design, or professional academic communication."
            ),
        }

        task_guides = {
            "Explain a topic": (
                "Create a prompt that asks the AI to explain the topic clearly and accurately. "
                "Encourage simple explanation, key concepts, examples, and step-by-step teaching where helpful."
            ),
            "Summarize notes": (
                "Create a prompt that asks the AI to turn the notes into an organized and useful summary. "
                "Encourage headings, bullet points, key takeaways, and study-friendly structure."
            ),
            "Make quiz questions": (
                "Create a prompt that asks the AI to generate useful quiz or practice questions from the content. "
                "Encourage a clear question set, varied question types when helpful, and an answer key."
            ),
            "Improve writing": (
                "Create a prompt that asks the AI to improve the writing for clarity, grammar, flow, and organization "
                "while preserving the original meaning."
            ),
            "Summarize a research paper": (
                "Create a prompt that asks the AI to summarize the paper in a structured academic format. "
                "Encourage sections such as objective, methodology, key findings, limitations, and significance."
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
                "Create a prompt that asks the AI to organize the notes into a clear outline. "
                "Encourage logical structure, headings, subheadings, and coherent progression of ideas."
            ),
            "Rewrite for clarity, formality, and precision": (
                "Create a prompt that asks the AI to rewrite the content with improved clarity, precision, and formal tone. "
                "Ensure the meaning is preserved while improving readability and professionalism."
            ),
        }

        audience_guide = audience_guides.get(
            audience,
            "The generated prompt should be clear, well-structured, and suitable for academic or professional use."
        )

        task_guide = task_guides.get(
            task_name,
            "Create a high-quality prompt that improves clarity, structure, and usefulness."
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

Requirements for the generated prompt:
- be clear, specific, and easy to use
- match the audience level and expected quality
- guide the AI to produce a strong, organized response
- encourage structured output when useful (headings, bullet points, sections, steps)
- preserve academic honesty and avoid encouraging cheating or dishonest work
- sound polished and ready to paste into an AI tool

Return only the final prompt.
"""

        response = self.client.responses.create(
            model="gpt-5.4",
            instructions=base_instructions,
            input=user_input,
        )

        return response.output_text.strip()