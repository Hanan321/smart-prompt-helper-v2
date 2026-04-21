from openai import OpenAI


class PromptGenerator:
    AUDIENCE_GUIDANCE = {
        "Middle school": (
            "Use simple language, short sentences, concrete examples, and a supportive tone. "
            "The final prompt should ask the AI to explain ideas in a friendly, age-appropriate way, "
            "break concepts into small steps, and avoid unnecessary jargon."
        ),
        "High school": (
            "Use a clear educational style with structured explanations, helpful definitions, "
            "moderate depth, and relevant examples. The final prompt should encourage organization, "
            "accuracy, and a tone suitable for secondary-level learning."
        ),
        "University/College": (
            "Use a formal academic tone, analytical thinking, and structured output. "
            "The final prompt should encourage clear reasoning, evidence-aware explanation, "
            "discipline-appropriate vocabulary, and college-level depth."
        ),
        "Higher education level": (
            "Use an advanced academic tone with synthesis, conceptual depth, and strong organization. "
            "The final prompt should ask for nuanced analysis, connections across ideas, "
            "and careful treatment of complexity."
        ),
        "Researchers": (
            "Use a scholarly tone with precision, methodological awareness, attention to limitations, "
            "and focus on contribution. The final prompt should support rigorous analysis, "
            "careful terminology, and research-grade structure."
        ),
    }

    TASK_GUIDANCE = {
        "Explain a topic": (
            "Create a prompt that asks the AI to explain the topic clearly, define key concepts, "
            "use appropriate examples, and organize the response for the selected audience."
        ),
        "Summarize notes": (
            "Create a prompt that asks the AI to turn notes into an organized summary with headings, "
            "key takeaways, important details, and a study-friendly structure."
        ),
        "Make quiz questions": (
            "Create a prompt that asks the AI to generate useful quiz or practice questions from the content, "
            "include a range of difficulty when appropriate, and provide an answer key."
        ),
        "Improve writing": (
            "Create a prompt that asks the AI to improve clarity, grammar, flow, structure, and readability "
            "while preserving the user's meaning and voice where appropriate."
        ),
        "Write an essay": (
            "Create a prompt that asks the AI to write or structure an essay with a clear thesis, "
            "organized paragraphs, relevant evidence placeholders, and an appropriate academic tone."
        ),
        "Generate study guide": (
            "Create a prompt that asks the AI to turn the material into a study guide with headings, "
            "key terms, explanations, review points, and practice questions where useful."
        ),
        "Create presentation outline": (
            "Create a prompt that asks the AI to build a presentation outline with slide-by-slide structure, "
            "key talking points, and audience-appropriate pacing."
        ),
        "Create flashcards": (
            "Create a prompt that asks the AI to turn the material into useful flashcards with questions, "
            "answers, key terms, and concise explanations."
        ),
        "Make a homework plan": (
            "Create a prompt that asks the AI to make a practical homework plan with priorities, "
            "time estimates, study steps, and a manageable sequence."
        ),
        "Turn notes into practice problems": (
            "Create a prompt that asks the AI to convert the material into practice problems "
            "with clear answers and explanations."
        ),
        "Draft a thesis statement": (
            "Create a prompt that asks the AI to draft and refine a focused thesis statement "
            "based on the topic, assignment goal, and available context."
        ),
        "Build an essay outline": (
            "Create a prompt that asks the AI to build a structured essay outline with a thesis, "
            "main points, evidence placeholders, and conclusion."
        ),
        "Create an annotated bibliography plan": (
            "Create a prompt that asks the AI to plan an annotated bibliography structure, "
            "source evaluation criteria, and annotation format."
        ),
        "Analyze an argument": (
            "Create a prompt that asks the AI to analyze an argument for claim, evidence, reasoning, "
            "assumptions, counterarguments, and possible weaknesses."
        ),
        "Prepare for an exam": (
            "Create a prompt that asks the AI to make an exam preparation plan with study priorities, "
            "review schedule, practice questions, and active recall strategies."
        ),
        "Summarize a research paper": (
            "Create a prompt that asks the AI to summarize a research paper in a structured format, "
            "including purpose, methods, findings, limitations, and significance."
        ),
        "Improve academic writing": (
            "Create a prompt that asks the AI to refine academic writing for clarity, coherence, "
            "grammar, formality, argument flow, and stronger scholarly tone."
        ),
        "Generate research questions": (
            "Create a prompt that asks the AI to generate clear, focused, researchable academic questions "
            "that fit the topic, field, and available evidence."
        ),
        "Refine a literature review": (
            "Create a prompt that asks the AI to improve the structure, synthesis, flow, transitions, "
            "gap identification, and scholarly framing of a literature review."
        ),
        "Turn notes into a structured academic outline": (
            "Create a prompt that asks the AI to organize notes into a clear academic outline "
            "with headings, subheadings, claims, and supporting points."
        ),
        "Rewrite for clarity, formality, and precision": (
            "Create a prompt that asks the AI to rewrite the content with improved clarity, formality, "
            "precision, concision, and coherence while preserving meaning."
        ),
        "Analyze research methods": (
            "Create a prompt that asks the AI to evaluate research methods, including design, sample, "
            "measures, analysis approach, strengths, weaknesses, and limitations."
        ),
        "Create a data analysis plan": (
            "Create a prompt that asks the AI to develop a data analysis plan with variables, methods, "
            "assumptions, checks, interpretation plan, and reporting structure."
        ),
        "Draft a discussion section": (
            "Create a prompt that asks the AI to draft or structure a discussion section that interprets findings, "
            "addresses limitations, explains implications, and proposes future work."
        ),
        "Prepare a conference presentation": (
            "Create a prompt that asks the AI to turn research content into a conference presentation structure "
            "with key claims, slide flow, and speaking notes."
        ),
        "Draft a journal abstract": (
            "Create a prompt that asks the AI to draft a concise journal-style abstract with background, "
            "objective, methods, results, and conclusion placeholders."
        ),
        "Prepare a conference proposal": (
            "Create a prompt that asks the AI to create a conference proposal with title, abstract, "
            "contribution, audience fit, keywords, and scholarly relevance."
        ),
        "Create a grant proposal outline": (
            "Create a prompt that asks the AI to outline a grant proposal with problem statement, aims, "
            "significance, approach, timeline, expected outcomes, and evaluation plan."
        ),
    }

    RESEARCHER_TASK_OVERRIDES = {
        "Summarize a research paper": (
            "For a researcher audience, create a prompt that asks for a rigorous scholarly summary including "
            "research problem, theoretical framing, methodology, data or corpus, analytical approach, "
            "key findings, limitations, validity concerns, contribution to the field, and future research directions."
        ),
        "Generate research questions": (
            "For a researcher audience, create a prompt that asks for advanced, research-grade questions that are "
            "specific, methodologically feasible, theoretically grounded, original, and suitable for scholarly inquiry."
        ),
        "Improve academic writing": (
            "For a researcher audience, create a prompt that asks for journal-level academic refinement, including "
            "precision, argument coherence, scholarly tone, methodological clarity, concision, and discipline-appropriate style."
        ),
    }

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Missing OpenAI API key.")
        self.client = OpenAI(api_key=api_key)

    def generate(self, audience: str, task_name: str, user_text: str) -> str:
        clean_text = user_text.strip()

        audience_guide = self.AUDIENCE_GUIDANCE.get(
            audience,
            "The generated prompt should be clear, well-structured, and suitable for academic or professional use.",
        )

        task_guide = self.TASK_GUIDANCE.get(
            task_name,
            "Create a high-quality prompt that improves clarity, structure, and usefulness.",
        )

        extra_guide = ""
        if audience == "Researchers":
            extra_guide = self.RESEARCHER_TASK_OVERRIDES.get(
                task_name,
                "For a researcher audience, emphasize scholarly precision, methodological awareness, limitations, "
                "and the likely contribution or significance of the work.",
            )

        system_instruction = f"""
You generate high-quality prompts for AI tools.

Audience:
{audience_guide}

Task:
{task_guide}

Extra:
{extra_guide}

Rules:
- Return ONLY the final prompt
- No explanations
- No extra text
- Write exactly one high-quality prompt that the user can copy and paste into ChatGPT or a similar AI tool
- If the user's input is short, vague, incomplete, or only a few words, infer the most likely academic or professional intent conservatively
- Do not ask follow-up questions
- Do not invent specific facts, sources, study results, citations, or personal details that were not provided
- Include helpful structure, context, role framing, and output instructions when useful
- Match the prompt's quality, complexity, tone, and structure to the selected audience
"""

        user_message = f"""
Audience: {audience}
Task: {task_name}

User content:
{clean_text if clean_text else "[No additional user content provided]"}
"""

        try:
            response = self.client.responses.create(
                model="gpt-5.4",
                instructions=system_instruction,
                input=user_message,
            )
            return response.output_text.strip()
        except Exception as exc:
            raise RuntimeError(f"Prompt generation failed: {exc}") from exc
