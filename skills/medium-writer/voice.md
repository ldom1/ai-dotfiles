# Voice

Tech. First person. Concrete commands and trade-offs. Useful to people who will actually run the setup (example: how to add their own skills in ai-dotfiles).

Gold standard: `~/ai-dotfiles/articles/ai-dotfiles-portable-ai-control-centre.md`.

## Hard rules

- Real code in fenced snippets, copied from a file that exists. Cite the path above the fence.
- No AI slop: no “In this article we’ll explore”, no empty “7 benefits” lists, no generic sample apps, no “delve / landscape / robust solution”.
- Do not sound like an AI. Short sentences. Name the cost of each choice.

## Review prompt (verbatim)

```
Please review the attached Medium article thoroughly and provide actionable
feedback to optimize its quality, engagement, and reach. Focus on incorporating
best-in-class practices for content creation, including:

Headline and Introduction:
Assess if the headline is compelling, clear, and optimized for Medium's audience and
SEO.
Evaluate the introduction to ensure it hooks readers effectively and previews
the value of the article.

Structure and Readability:
Analyze the article's flow, organization, and formatting (e.g., use of subheadings,
bullet points, and paragraph length).
Suggest ways to make the article skimmable while maintaining depth and clarity.

Content Quality:
Check for accuracy, relevance, and depth in the content.
Highlight opportunities to include data, examples, or storytelling to enhance
credibility and engagement.

Call-to-Actions (CTAs):
Recommend effective CTAs to drive interactions (e.g., claps, comments, shares,
or newsletter sign-ups).

SEO and Keywords:
Identify if the article targets relevant keywords for its niche and suggest
optimizations for Medium's search algorithm.
Ensure the use of meta descriptions, alt text for images, and appropriate tagging.

Tone and Voice:
Ensure the writing style aligns with the intended audience and Medium's platform
preferences.
Suggest improvements for clarity, relatability, and impact.

DO NOT SOUND LIKE YOU ARE AN AI

OUTPUT
Only propose specific, actionable changes that can be implemented to maximize
the article's reach, engagement, and ranking on Medium. Please include examples or
references to successful Medium articles when applicable.

Propose also : 3 alternatives titles
```
