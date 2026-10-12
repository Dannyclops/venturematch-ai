# Public demo deployment

The `render.yaml` Blueprint hosts the browser and FastAPI backend as one web
service. The free matching engine is available to every visitor. The paid
AI-assisted option uses the server-side OpenAI API key and requires a reviewer
access code. Never place the OpenAI key in the repository, browser, or submission.

1. Sign in to [Render Dashboard](https://dashboard.render.com/) and choose
   **New → Blueprint**. Connect `Dannyclops/venturematch-ai` on `main` and
   review the free `venturematch-ai-demo` web service.
2. Render prompts for two secret environment values from `render.yaml`:
   `OPENAI_API_KEY` (your existing key) and
   `VENTUREMATCH_DEMO_ACCESS_CODE` (a new code you choose for reviewers).
   Set both in the Render form. The Blueprint also enables the live agent and
   refuses to start if the access code is missing.
3. Apply the Blueprint and wait for the deploy to become live. Open its
   actual `https://...onrender.com/` URL. Do not assume the service name alone
   determines the URL; copy it from Render.
4. Test **Free matching engine** first. Then select **AI-assisted (uses credits)**,
   enter the reviewer code, confirm one billable search, and wait for a ranked
   result. Check `/api/health` if the page cannot connect.
5. Submit the verified live URL with the temporary reviewer access code beside
   it, so judges can use the AI-assisted option. If the submission has a private
   judge note, put the code there. A code in a public submission is public too;
   rotate it after judging. Never submit the OpenAI API key.

Suggested submission wording (replace both placeholders after deployment):

> Live demo: `https://YOUR-ACTUAL-SERVICE.onrender.com/`
>
> To try the AI agent, choose **AI-assisted (uses credits)** and enter reviewer
> access code: `YOUR-TEMPORARY-CODE`. The page points back to this note.

The first request to a free Render web service after inactivity can take time
because it spins down after 15 minutes. Reopen the link shortly before judging.
The fictional catalog and FX snapshot are bundled with the repository; there
is no database or user account system. The access code is a lightweight demo
gate, not a production identity system. It can be rotated in Render's environment
settings without changing the public URL.
