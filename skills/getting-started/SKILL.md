---
name: getting-started
description: Explain AskSia exam practice and vocabulary review, and help a learner connect their Sia account through the host's OAuth flow. Use for first-time setup, connection questions, or choosing an AskSia learning activity.
---

# Getting started with AskSia

Introduce AskSia briefly: it provides stored exam questions with server grading, vocabulary cards, recall recording, and saved study progress. Help the learner choose practice, vocabulary review, or a progress check.

## Connect the account

Use the AskSia connection included with the installed plugin. The host may add a prefix to its tool names; discover its available tools and schemas rather than constructing a platform-specific tool name.

If the connection needs authorization, direct the learner to the host's connection or sign-in action. They sign in to Sia in the browser, review the requesting client's permissions, and choose whether to approve. The host handles the OAuth return and tokens. Use the environment configured in the installed package; do not switch its endpoint or ask the learner to paste passwords, API keys, authorization codes, or tokens into chat.

If authorization is canceled, expired, or unsuccessful, explain what is known and let the learner restart the host's connection flow when ready. Do not report a successful connection until the host or an authorized tool call confirms it. A working setup guide or installed package alone does not establish a working connection.

## Choose a useful first step

- For existing plans and progress, call `get_my_exams`. Explain the returned exam, package-purchase status, existing score estimate, target, and next unfinished day. A missing value means no saved value is available. This is the learner's plan list, not a full exam catalog.
- For practice, establish the desired exam and use `get_practice_questions`, followed by `submit_answer` after the learner answers. Follow the packaged exam-practice workflow: one question at a time, with grading and explanation after submission.
- For vocabulary, establish the exam and use `get_vocab_cards`, followed by `record_vocab_review` only after explicit recall feedback. Follow the packaged vocab-review workflow: recall first, reveal second, record third.
- For vocabulary counts only, call `get_vocab_progress`; a separate practice plan is not required.

Let the backend decide which exams and content are available to this account. An empty plan list does not prevent asking for an exam; an empty question or card list does not authorize creating substitute bank content. Keep the current request limited to the learner's chosen activity.

Stored practice uses the service's existing credits and access rules. Describe a credit or rate-limit response using the message and link the service returns, then pause automatic calls. Do not promise a welcome bonus, availability for every exam, or a completed deployment based solely on the plugin's instructions.

Report successful learning actions from tool results. Keep failures distinct from an empty result or saved progress, and never invent a grade, a review write, or an account state.
