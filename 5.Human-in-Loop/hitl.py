"""Human-in-the-loop helpers: tools call confirm() or ask() to prompt the user."""

from langgraph.types import interrupt

# "ui" picks the element that renders the prompt; add a .jsx and register it here.
UI_FORM = "form"

RENDERERS = {
    UI_FORM: "AskForm",
}

DEFAULT_RENDERER = RENDERERS[UI_FORM]


def ask(questions):
    """Ask {id, header, question, options[, multiSelect, allowOther]} dicts, return {id: answer}."""
    # Cancel or timeout returns {"cancelled": True}, so no question id is present.
    answers = interrupt({"ui": UI_FORM, "questions": questions})
    return answers if isinstance(answers, dict) else {}


def confirm(
    question,
    header="Approve",
    yes_label="Yes",
    yes_description="",
    no_label="No",
    no_description="",
):
    """Single yes/no gate. Returns True only if the user explicitly approved."""
    answers = ask([
        {
            "id": "confirm",
            "header": header,
            "question": question,
            "options": [
                {"value": "yes", "label": yes_label, "description": yes_description},
                {"value": "no", "label": no_label, "description": no_description},
            ],
        }
    ])
    return answers.get("confirm") == "yes"
