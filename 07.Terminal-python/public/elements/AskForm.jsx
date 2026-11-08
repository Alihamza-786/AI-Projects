import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// props.command comes from interrupt({"command": ...}) in hitl.py.
// submitElement(...) sends the answer back; it becomes the return value of interrupt().
export default function AskForm() {
  const [editing, setEditing] = useState(false);
  const [command, setCommand] = useState(props.command);
  const [answer, setAnswer] = useState(null);

  function send(result) {
    setAnswer(result);
    submitElement(result);
  }

  // After answering, just show what the user chose
  if (answer) {
    const text = {
      yes: `Approved: ${props.command}`,
      no: `Rejected: ${props.command}`,
      edit: `Edited and approved: ${answer.command}`,
    }[answer.action];

    return <div className="rounded-lg border bg-card p-3 text-sm text-muted-foreground">{text}</div>;
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border bg-card p-4">
      <p className="text-sm font-medium">Do you allow me to run this command?</p>

      {editing ? (
        <Input
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && command.trim() && send({ action: "edit", command: command.trim() })}
          className="font-mono"
          autoFocus
        />
      ) : (
        <pre className="rounded-md bg-muted p-3 font-mono text-sm whitespace-pre-wrap">{props.command}</pre>
      )}

      {editing ? (
        <div className="flex gap-2">
          <Button disabled={!command.trim()} onClick={() => send({ action: "edit", command: command.trim() })}>
            Run edited command
          </Button>
          <Button variant="outline" onClick={() => { setEditing(false); setCommand(props.command); }}>
            Back
          </Button>
        </div>
      ) : (
        <div className="flex gap-2">
          <Button onClick={() => send({ action: "yes" })}>Yes</Button>
          <Button variant="outline" onClick={() => send({ action: "no" })}>No</Button>
          <Button variant="secondary" onClick={() => setEditing(true)}>Edit</Button>
        </div>
      )}
    </div>
  );
}
