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
            "If the user's input is short, vague, incomplete, or only a few words, infer the most likely academic or professional intent conservatively and turn it into a strong usable prompt. "
            "Do not ask follow-up questions. Instead, make reasonable assumptions based on the selected audience, task, and user content. "
            "Add helpful structure, context, and output instructions when needed, but do not invent specific facts, sources, or personal details that were not provided. "
            "Whenever useful, write the prompt so it naturally includes the AI role, the user's goal, the provided content, and the desired output format. "
            "Adapt the prompt quality, complexity, tone, and structure to match the selected audience. "
            "If the user's request is very broad, turn it into a practical, guided prompt that helps the AI produce a strong first draft. "
            "Return only the final prompt."
        )

        audience_guides = {
            "Middle school": (
                "The generated prompt should ask for a response that is simple, supportive, age-appropriate, and easy to follow. "
                "Prefer plain language, clear examples, and step-by-step explanation when useful."
            ),
            "High school": (
                "The generated prompt should ask for a response that is clear, supportive, easy to follow, and educational. "
                "Prefer plain language, step-by-step explanation when useful, and practical structure."
            ),
            "University/College": (
                "The generated prompt should ask for a response that is clear, well-structured, educational, and suitable for college-level academic work. "
                "Encourage useful organization, accurate explanation, and appropriate academic tone."
            ),
            "Higher education level": (
                "The generated prompt should ask for a response that is academically strong, well-structured, and appropriately detailed. "
                "Encourage analytical depth, organization, and formal academic tone."
            ),
            "Researchers": (
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
            "Write an essay": (
                "Create a prompt that asks the AI to write or help structure an essay with a clear thesis, organized paragraphs, and an appropriate academic tone."
            ),
            "Generate study guide": (
                "Create a prompt that asks the AI to turn the material into a study guide with headings, key terms, and review points."
            ),
            "Create presentation outline": (
                "Create a prompt that asks the AI to create a clear presentation outline with slide-by-slide structure and key talking points."
            ),
            "Create flashcards": (
                "Create a prompt that asks the AI to turn the material into useful flashcards with questions, answers, and key terms."
            ),
            "Make a homework plan": (
                "Create a prompt that asks the AI to make a practical homework plan with prioritized tasks, timing, and study steps."
            ),
            "Turn notes into practice problems": (
                "Create a prompt that asks the AI to convert the material into practice problems with clear answers and explanations."
            ),
            "Draft a thesis statement": (
                "Create a prompt that asks the AI to draft and refine a focused thesis statement based on the topic and assignment goal."
            ),
            "Build an essay outline": (
                "Create a prompt that asks the AI to build a structured essay outline with a thesis, main points, evidence placeholders, and conclusion."
            ),
            "Create an annotated bibliography plan": (
                "Create a prompt that asks the AI to plan an annotated bibliography structure, source evaluation criteria, and annotation format."
            ),
            "Analyze an argument": (
                "Create a prompt that asks the AI to analyze an argument for claim, evidence, reasoning, assumptions, and possible weaknesses."
            ),
            "Prepare for an exam": (
                "Create a prompt that asks the AI to make an exam preparation plan with study priorities, practice questions, and review schedule."
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
            "Analyze research methods": (
                "Create a prompt that asks the AI to evaluate research methods, including design, sample, measures, analysis approach, strengths, and limitations."
            ),
            "Create a data analysis plan": (
                "Create a prompt that asks the AI to develop a data analysis plan with variables, methods, assumptions, checks, and reporting structure."
            ),
            "Draft a discussion section": (
                "Create a prompt that asks the AI to draft or structure a discussion section that interprets findings, limitations, implications, and future work."
            ),
            "Prepare a conference presentation": (
                "Create a prompt that asks the AI to turn research content into a conference presentation structure with key claims and speaking notes."
            ),
            "Draft a journal abstract": (
                "Create a prompt that asks the AI to draft a concise journal-style abstract with background, objective, methods, results, and conclusion placeholders."
            ),
            "Prepare a conference proposal": (
                "Create a prompt that asks the AI to create a conference proposal with title, abstract, contribution, audience fit, and keywords."
            ),
            "Create a grant proposal outline": (
                "Create a prompt that asks the AI to outline a grant proposal with problem statement, aims, significance, approach, timeline, and expected outcomes."
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
{clean_text if clean_text else "[No additional user content provided]"}

Important handling rules:
- The user may not be familiar with AI tools or prompt writing.
- The user may provide only one or two words.
- If the user input is vague, short, or incomplete, infer the most likely goal based on the selected task and audience.
- Expand the request into a useful, beginner-friendly, copy-paste-ready prompt.
- Do not ask follow-up questions.
- Do not invent factual details such as study results, references, or personal background.
- When needed, include placeholders or flexible wording such as "based on the text below" or "using the topic provided."

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
