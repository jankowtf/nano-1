I'm dreaming of accomplishing this:

Coming up with a Python package design that is the code equivalent of "antifragile nanobots." I call it "nanobricks": atomic, self-sufficient components that are:

1. **Simple** — Nanobricks are designed and implemented in a straightforward way
   and thus simple/easy for both humans and AIs to reason about in terms of
   architecture and implementation.
2. **Standardized** — Nanobricks interfaces are consistent, like a "Lego Connector
   Mechanism" for code. We need to find the right design patterns that offer
   standardization in the interface while also allowing for maximum flexibility
   regarding the implementation.
3. **Composable** — Nanobricks can be easily combined to form more complex
   components. Examples: integrating API functionality into an existing API,
   adding Streamlit features to an existing app, or piping nanobricks together
   to create a workflow.
4. **Batteries included** - Nanobricks ship with self-contained, modular and
   composable fucnctionality for powering their own:
   1. API (FastAPI)
   2. CLI (Typer)
   3. Frontend (Streamlit; app or page or tab or subtab)
   4. DB interaction layer (SQLModel)
5. **Scaffoldable for end-to-end usage in an instant** - Nanobricks use the
   absolute very best design patterns and scaffold techniques to "just work" out
   of the box. Inspired by Rails. Probably through go-task plus a set of
   cursorrules or similar. The actual functionality to be implemented can then
   be integrated into the scaffold step-by-step by humans and AI coding agents

This is just my initial (!) concept. It's kind of hard to put my ideas into
writing. I need to flesh this idea out and need your help in doing so. Let's try
to synthesize the concept into `@nanobricks.mdc`.

Let's have a conversation about this. Remember to snapshot and synthesize
important aspects as we go along. I really need your help on this

I want to create a revolutionary, antifragile and somewhat organic coding
paradigm with you

---

Very important aspects:

1. every nanobrick must materialize as a python package based on the usage of
   `uv`. Look at rules related to src-based project layouts, and pyproject.toml
2. modues should start out as directory-based modules. Below should be rather
   file-based modules instead of deeply nested other directory-based to keep the
   architecture "simple". But I'm not opposed to more complex module setups if
   its better suited for the task
3. We always use absolute imports unless you argue agains ist
4. There are a list of design patterns used by other repos which I like. Take a
   look at them and assess if/which ones we should use. I'm fine with you
   deciding any way you want - including not to use any of them at all or
   different ones.
