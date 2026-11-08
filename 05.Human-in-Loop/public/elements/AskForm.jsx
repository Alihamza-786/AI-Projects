import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Check, ChevronRight, CornerDownLeft } from "lucide-react";

// Draws whatever spec arrives in props.questions (see hitl.py); submitElement()
// becomes the return value of interrupt() inside the tool that asked.
export default function AskForm() {
  const questions = props.questions || [];

  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [picked, setPicked] = useState([]);
  const [other, setOther] = useState("");
  const [done, setDone] = useState(false);

  const q = questions[index];
  if (!q) return null;

  const key = q.id || String(index);
  const isMulti = !!q.multiSelect;

  function advance(value) {
    const next = { ...answers, [key]: value };
    setAnswers(next);
    setPicked([]);
    setOther("");

    if (index + 1 < questions.length) {
      setIndex(index + 1);
    } else {
      setDone(true);
      submitElement(next);
    }
  }

  function toggle(value) {
    setPicked(picked.includes(value)
      ? picked.filter((v) => v !== value)
      : [...picked, value]);
  }

  // Answered questions stay visible above the current one.
  const history = questions.slice(0, index).map((prev, i) => {
    const answer = answers[prev.id || String(i)];
    return (
      <div key={i} className="flex items-center gap-2 text-sm text-muted-foreground">
        <Check className="h-3.5 w-3.5 shrink-0" />
        <span className="font-medium">{prev.header || prev.question}</span>
        <span className="truncate">{Array.isArray(answer) ? answer.join(", ") : answer}</span>
      </div>
    );
  });

  if (done) {
    return (
      <div className="flex flex-col gap-1.5 rounded-lg border bg-card p-3">
        {history}
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Check className="h-3.5 w-3.5 shrink-0" />
          <span className="font-medium">{q.header || q.question}</span>
          <span className="truncate">
            {Array.isArray(answers[key]) ? answers[key].join(", ") : answers[key]}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border bg-card p-4">
      {history.length > 0 && <div className="flex flex-col gap-1.5 pb-1">{history}</div>}

      <div className="flex items-center gap-2">
        {q.header && <Badge variant="secondary">{q.header}</Badge>}
        {questions.length > 1 && (
          <span className="text-xs text-muted-foreground">
            {index + 1} of {questions.length}
          </span>
        )}
      </div>

      <p className="text-sm font-medium">{q.question}</p>

      <div className="flex flex-col gap-2">
        {(q.options || []).map((opt) => {
          const selected = isMulti && picked.includes(opt.value);
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => (isMulti ? toggle(opt.value) : advance(opt.value))}
              className={`flex w-full items-start gap-3 rounded-md border p-3 text-left transition-colors hover:bg-accent ${
                selected ? "border-primary bg-accent" : ""
              }`}
            >
              <div
                className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
                  selected ? "border-primary bg-primary text-primary-foreground" : ""
                }`}
              >
                {selected && <Check className="h-3 w-3" />}
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-sm font-medium leading-none">{opt.label || opt.value}</span>
                {opt.description && (
                  <span className="text-xs text-muted-foreground">{opt.description}</span>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {q.allowOther && (
        <div className="flex items-center gap-2">
          <Input
            placeholder="Other..."
            value={other}
            onChange={(e) => setOther(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && other.trim()) advance(other.trim());
            }}
          />
          <Button
            size="sm"
            variant="secondary"
            disabled={!other.trim()}
            onClick={() => advance(other.trim())}
          >
            <CornerDownLeft className="h-3.5 w-3.5" />
          </Button>
        </div>
      )}

      {isMulti && (
        <Button size="sm" disabled={picked.length === 0} onClick={() => advance(picked)}>
          Continue
          <ChevronRight className="ml-1 h-3.5 w-3.5" />
        </Button>
      )}
    </div>
  );
}
