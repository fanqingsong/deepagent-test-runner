---
name: content-writing
description: Write blog posts, social media content, and articles. Use when the user asks to write, draft, or create any written content — blog posts, LinkedIn posts, tweets, articles, or thought leadership pieces.
---

# Content Writing Skill

## When to Use

Delegate to the `content-builder` subagent when the user asks to:
- Write a blog post or article
- Create a LinkedIn post
- Write a tweet or Twitter/X thread
- Draft any long-form or social content

## How to Delegate

Use the `task` tool with `subagent_type: "content-builder"`.

For blog posts:
```
task(
    subagent_type="content-builder",
    description="Write a blog post about [TOPIC]. Tone: professional. Audience: developers."
)
```

For social media:
```
task(
    subagent_type="content-builder",
    description="Write a LinkedIn post about [TOPIC]. Tone: professional."
)
```

## What the Subagent Does

The content-builder subagent:
1. **Researches first** — searches the web for current information on the topic
2. **Writes content** — generates structured content based on research
3. **Returns the result** — complete markdown content ready to use

## Supported Content Types

| Type | Platform | Format |
|------|----------|--------|
| Blog post | N/A | Full markdown with headers, hook, sections, CTA |
| LinkedIn | linkedin | Professional post with hashtags |
| Twitter/X | twitter | Tweet or thread with hook |

## Tone Options

- `professional` — formal, authoritative (default)
- `casual` — friendly, conversational
- `technical` — code-heavy, precise
- `thought-provoking` — opinionated, discussion-starting

## Quality Checklist

Before returning content to the user, verify:
- [ ] Content has a clear hook/opening
- [ ] Main points are well-structured
- [ ] Includes actionable takeaways or CTA
- [ ] Language matches the user's request language
