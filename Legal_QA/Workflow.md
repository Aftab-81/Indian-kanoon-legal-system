# Feature Enhancement: Redesign the Legal QA System UI & Implement Intent-Based LLM Prompt Routing

## Objective

Redesign and modernize the **Legal QA System** by enhancing both the **frontend UI** and the **backend architecture** while preserving the existing **RAG workflow (PDF → Smart Chunking → FAISS → Semantic Search → LLM → Response)**.

The objective is to create a production-ready Legal QA experience with a modern conversational interface and an intelligent backend capable of handling different user intents without affecting any existing functionality.

---

# 1. UI/UX Redesign

Use the current Legal QA module as the foundation, but redesign it to provide a cleaner, more modern, and conversational experience while maintaining the existing Judicial Insight Engine theme.

## General Requirements

- Maintain the existing navy blue and white design language.
- Use a clean card-based layout with consistent spacing, padding, border radius, and shadows.
- Improve typography hierarchy.
- Ensure responsive behavior across different screen sizes.
- Add smooth hover effects and loading animations.
- Do **not** remove any existing functionality.

---

# 2. Upload Case Page

Redesign the upload experience to feel more modern and intuitive.

## Requirements

- Modern drag-and-drop upload area.
- Improved upload icon and supporting illustration.
- Display supported file type (PDF).
- Display maximum file size (if applicable).
- Upload progress indicator.
- Indexing progress with individual steps:

  - Uploading PDF
  - Extracting Text
  - Smart Chunking
  - Creating Embeddings
  - Building FAISS Index
  - Ready for Questions

- Display a success animation once indexing completes.

---

# 3. Document Information Card

After indexing completes, replace the upload section with a polished document summary card.

Display:

- Document Name
- Court
- Date
- Total Pages
- File Size
- Indexed Time
- Language
- Status
- Change Document button

The card should be visually clean and easy to scan.

---

# 4. Chat Interface

Completely redesign the Legal QA chat interface.

## Requirements

- ChatGPT/Claude/Gemini-inspired layout.
- Clearly distinguish User and AI messages.
- Rounded message bubbles.
- Better timestamps.
- User avatar and AI avatar.
- Auto-scroll to newest message.
- Copy response button.
- Regenerate response button.
- Loading animation while AI is generating.
- Typing indicator.
- Better empty-state before the first question.
- Preserve conversation history correctly.

---

# 5. Question Input Area

Improve the input experience.

Requirements:

- Larger input box.
- Multi-line support.
- Enter to send.
- Shift + Enter for new line.
- Send button with icon.
- Disable send button while the AI is responding.
- Optional character counter.

---

# 6. References Panel

Redesign the references section.

Display:

- Retrieved chunk preview
- Page number
- Similarity score
- Expand/Collapse functionality
- Highlight retrieved text
- Improved styling

---

# 7. History Page

Improve the History page.

Display:

- Previous conversations
- Uploaded document
- Date
- Number of questions asked
- Conversation preview
- Search history
- Delete conversation
- Continue conversation

---

# 8. Preserve Existing Backend Architecture

Maintain the existing architecture.

```text
PDF
   ↓
Smart Chunking
   ↓
Embedding Generation
   ↓
FAISS
   ↓
Semantic Search
   ↓
LLM
   ↓
Frontend
```

Do **not** remove or modify:

- Smart Chunking
- Embedding Generation
- FAISS Vector Database
- Semantic Search
- Existing APIs
- Existing Business Logic
- Conversation History
- Upload Workflow

---

# 9. Implement Intent-Based Prompt Routing

Introduce an **Intent Detection** layer before the existing RAG pipeline.

The Intent Detection component **must never generate responses**.

Its only responsibility is identifying the user's intent and selecting the correct prompt template.

---

## Supported Intents

### Greeting

Examples:

- Hello
- Hi
- Hey
- Good Morning
- Good Evening

Behavior:

- Detect Greeting intent.
- Route to the Greeting Prompt.
- The **LLM** generates the response.
- Do **not** hardcode greetings.

---

### Summary

Examples:

- Summarize this case.
- Give me a brief overview.
- Explain this judgement.
- What is this case about?

Behavior:

- Detect Summary intent.
- Route to the Summary Prompt.
- The **LLM** generates the structured summary.

---

### Document Question

Examples:

- Who filed the appeal?
- What is the final judgement?
- What legal issues were involved?
- Explain Section 302.

Behavior:

Continue using the existing RAG workflow:

- Semantic Search
- Retrieve Relevant Chunks
- Prompt Builder
- LLM
- Response

---

# 10. Prompt Templates

Implement reusable prompt templates.

---

## Greeting Prompt

The LLM should:

- Respond warmly.
- Maintain a professional tone.
- Invite the user to ask questions about the uploaded judgement.

---

## Summary Prompt

The LLM should generate a structured summary covering:

- Facts
- Legal Issues
- Arguments
- Court's Reasoning
- Final Judgement

---

## Document QA Prompt

Continue using the existing RAG architecture.

The LLM must:

- Answer **only** using the retrieved context.
- Clearly state when information is unavailable.
- Never hallucinate.

---

# 11. Backend Flow

Implement the following architecture.

```text
User Input
      │
      ▼
Request Validation
      │
      ▼
Intent Detection
      │
      ├──────────────► Greeting Prompt
      │                      │
      │                      ▼
      │                    OpenAI
      │
      ├──────────────► Summary Prompt
      │                      │
      │                      ▼
      │                    OpenAI
      │
      └──────────────► Document QA
                             │
                             ▼
                    Semantic Search (FAISS)
                             │
                             ▼
                  Retrieve Relevant Chunks
                             │
                             ▼
                      Prompt Builder
                             │
                             ▼
                           OpenAI
                             │
                             ▼
                    Response Cleaning
                             │
                             ▼
                   Response Validation
                             │
                             ▼
                          Frontend
```

---

# 12. Response Handling

Ensure that:

- Every user-visible response is generated by the LLM.
- No hardcoded greetings.
- No hardcoded summaries.
- Remove markdown artifacts.
- Remove escaped characters.
- Remove malformed JSON.
- Never expose Python dictionaries.
- Never expose backend objects.
- Never expose internal LLM responses.

Only return clean responses to the frontend.

---

# 13. Structured Logging

Implement consistent logging throughout the new workflow.

Log:

- Incoming request
- Intent detected
- Selected prompt template
- Semantic Search execution
- Retrieved chunk count
- Similarity scores
- LLM request
- LLM response time
- Response validation
- Final response
- Errors with stack traces

---

# 14. Performance

Ensure:

- Greeting requests bypass FAISS retrieval while still using the LLM.
- Summary requests use the appropriate processing flow.
- Document questions continue using Semantic Search.
- No unnecessary retrieval operations.
- Existing performance remains unaffected.

---

# 15. Maintain Existing Functionality

The following functionality **must remain unchanged**:

- PDF Upload
- Smart Chunking
- Embedding Generation
- FAISS Index
- Semantic Search
- Conversation History
- Language Selection
- Upload & Index workflow
- Existing APIs
- Existing Business Logic

No existing feature should regress.

---

# 16. Verification Checklist

After implementation, perform comprehensive end-to-end testing before considering the task complete.

Verify that:

- ✅ PDF upload works correctly.
- ✅ Smart Chunking functions correctly.
- ✅ Embeddings are generated successfully.
- ✅ FAISS indexing remains unchanged.
- ✅ Greeting intent is correctly detected.
- ✅ Greeting Prompt is selected.
- ✅ Greeting response is generated by the LLM.
- ✅ Summary intent is correctly detected.
- ✅ Summary Prompt is selected.
- ✅ Summary response is generated by the LLM.
- ✅ Document questions continue using Semantic Search.
- ✅ Prompt routing functions correctly for every supported intent.
- ✅ Retrieved chunks remain accurate.
- ✅ Response Cleaning removes unwanted formatting artifacts.
- ✅ Response Validation prevents malformed responses.
- ✅ Conversation History remains intact.
- ✅ References are displayed correctly.
- ✅ UI is responsive and visually consistent.
- ✅ No frontend regressions.
- ✅ No backend regressions.
- ✅ No exceptions or runtime errors.
- ✅ Existing functionality remains fully intact.

---

# 17. Final Validation

Once the implementation is complete:

- Thoroughly test each frontend component individually.
- Thoroughly test each backend component individually.
- Perform complete end-to-end testing of the entire workflow.
- Verify every supported intent.
- Verify all existing features still work exactly as before.
- Resolve any issues discovered during testing before marking the implementation as complete.