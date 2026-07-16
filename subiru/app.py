from datetime import datetime, timezone

from flask import Flask, redirect, render_template, request, url_for, flash

from owners import OWNERS
from storage import (
    STATUSES,
    create_task,
    load_tasks,
    save_tasks,
    update_status,
    update_task,
    find_task,
)
import tuna_log

app = Flask(__name__)
app.secret_key = "subiru-dev-secret"

STALE_DAYS = 3


def _age_days(iso_timestamp: str) -> float:
    then = datetime.fromisoformat(iso_timestamp)
    return (datetime.now(timezone.utc) - then).total_seconds() / 86400


def _is_stale(task) -> bool:
    if task.status == "done":
        return False
    return _age_days(task.updated_at) > STALE_DAYS


@app.route("/")
def index():
    tasks = load_tasks()
    tasks_by_owner = {owner: [] for owner in OWNERS}
    for task in tasks:
        tasks_by_owner.setdefault(task.owner, []).append(task)
    stale_ids = {t.id for t in tasks if _is_stale(t)}
    return render_template(
        "index.html",
        tasks_by_owner=tasks_by_owner,
        owners=OWNERS,
        statuses=STATUSES,
        all_tasks=tasks,
        stale_ids=stale_ids,
    )


@app.route("/tasks", methods=["POST"])
def add_task():
    title = request.form["title"].strip()
    owner = request.form["owner"]
    notes = request.form.get("notes", "").strip()
    depends_on = [int(x) for x in request.form.getlist("depends_on") if x]

    if not title:
        flash("A task needs a title.")
        return redirect(url_for("index"))

    tasks = load_tasks()
    task = create_task(tasks, title, owner, depends_on, notes)
    tuna_log.append_change(f"{owner} added a new task called '{title}'.")
    return redirect(url_for("index"))


@app.route("/tasks/<int:task_id>/status", methods=["POST"])
def change_status(task_id):
    new_status = request.form["status"]
    tasks = load_tasks()
    task = find_task(tasks, task_id)
    if task is None:
        flash("That task doesn't exist anymore.")
        return redirect(url_for("index"))

    old_status = task.status
    ok, blocking = update_status(tasks, task_id, new_status)
    if not ok:
        names = ", ".join(f"'{b}'" for b in blocking)
        flash(f"Can't move '{task.title}' to {new_status} yet — it's waiting on {names} to be done first.")
        return redirect(url_for("index"))

    if new_status == "done":
        tuna_log.append_change(f"{task.owner} finished '{task.title}'.")
    else:
        tuna_log.append_change(f"{task.owner} moved '{task.title}' from {old_status} to {new_status}.")
    return redirect(url_for("index"))


@app.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
def edit_task(task_id):
    tasks = load_tasks()
    task = find_task(tasks, task_id)
    if task is None:
        flash("That task doesn't exist anymore.")
        return redirect(url_for("index"))

    if request.method == "POST":
        title = request.form["title"].strip()
        owner = request.form["owner"]
        notes = request.form.get("notes", "").strip()
        depends_on = [int(x) for x in request.form.getlist("depends_on") if x and int(x) != task_id]

        if not title:
            flash("A task needs a title.")
            return redirect(url_for("edit_task", task_id=task_id))

        update_task(tasks, task_id, title, owner, depends_on, notes)
        tuna_log.append_change(f"{owner} updated the details on '{title}'.")
        return redirect(url_for("index"))

    other_tasks = [t for t in tasks if t.id != task_id]
    return render_template("task_form.html", task=task, owners=OWNERS, other_tasks=other_tasks)


if __name__ == "__main__":
    app.run(debug=True)
