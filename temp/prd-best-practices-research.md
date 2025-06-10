# PRD Best Practices & Structure Research

## Executive Summary

Based on current industry research, Product Requirements Documents (PRDs) are evolving to support both traditional human collaboration and modern AI-assisted development workflows. This research covers best practices, structure templates, and the emerging concept of AI-driven PRDs.

## Key PRD Components & Structure

### **Core PRD Template Structure**

#### 1. **Problem Alignment Section**

- **Clear Problem Statement**: Describe the specific problem or opportunity you're solving
- **Business Context**: Why is it important to users and business? What insights drive this?
- **High-level Approach**: Brief overview of solution direction without diving into implementation
- **Goals & Success Metrics**: Define measurable outcomes and success criteria

#### 2. **Solution Alignment Section**

- **Key Features**: Organized list of features with clear priorities
- **Key Flows**: Visual mockups, user journeys, and detailed use cases
- **Open Issues & Decisions**: Track controversial decisions, tradeoffs, and unresolved questions

#### 3. **Launch Readiness Section**

- **Key Milestones**: Timeline with dogfood, beta, and launch phases
- **Launch Checklist**: Cross-functional considerations (support, growth, marketing, security, platform)

### **Figma's Modern PRD Template Example**

**Project Data Section:**

- Team, contributors, status, shipping timeline
- TL;DR summary for quick context

**Problem Alignment:**

- Problem definition with user/business impact
- High-level approach explanation
- Clear success metrics

**Solution Alignment:**

- Feature breakdown with priorities
- Visual flows and mockups
- Decision documentation

**Launch Readiness:**

- Milestone tracking with audiences
- Comprehensive cross-functional checklist

## AI-Assisted PRD Development

### **Traditional vs. AI-Driven PRDs**

| Aspect         | Traditional PRDs                | AI-Driven PRDs                        |
| -------------- | ------------------------------- | ------------------------------------- |
| **Purpose**    | Human stakeholder alignment     | Human-AI collaboration bridge         |
| **Content**    | Unstructured text/images        | Structured, machine-parseable prompts |
| **Focus**      | Human comprehension             | Optimizing human-AI workflows         |
| **Tools**      | Notion, Jira, whiteboards       | GitHub, ChatGPT, Cursor, Claude Code  |
| **Challenges** | Human understanding differences | Context limits, prompt quality needs  |

### **AI Prompting Best Practices for PRDs**

#### **Initial Draft Generation**

```
"You are a product management expert. Help me write a comprehensive Product Requirement Document (PRD) for [project name]. Please include sections like objectives, key features, user stories, technical requirements, success metrics, and any potential risks or dependencies. Ensure the language is clear and concise, and provide suggestions for improving the document as we go."
```

#### **Improvement & Refinement**

```
"You are a product management expert. I have an existing Product Requirement Document (PRD) for [project name], and I need your help to make it significantly better. Please review the document in detail, focusing on the clarity and effectiveness of the objectives, key features, user stories, and technical requirements. Highlight any areas where the content can be more concise or where additional detail is needed. I'd also like feedback on potential gaps, overlooked risks, dependencies, and how to strengthen the success metrics. Provide actionable suggestions to improve the overall structure, readability, and alignment with industry best practices."
```

### **AI-Driven PRD Evolution: The "G3 Framework"**

**1. Guideline: Shared AI-Human Understanding**

- Comprehensive knowledge base with project context
- Technical rationale and architectural decisions
- Consistent foundation for both AI and human team members

**2. Guidance: Methodology for Evolving Prompts**

- Structured approach for converting abstract ideas to precise AI instructions
- Annotated prompt examples and pattern libraries
- Contextual best practices and pitfall warnings

**3. Guardrails: AI-Assisted Code Reviews**

- Automated evaluation standards for code quality
- Project-specific risk mitigation checkpoints
- AI-driven preliminary reviews before human oversight

## Modern PRD Best Practices

### **Quality Elements**

#### **Specificity Over Vagueness**

| Poor                                               | Good                                                                                                                                                                                                                                                                                                                                                   |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| "add tests for foo.py"                             | "write a new test case for foo.py, covering the edge case where the user is logged out. avoid mocks"                                                                                                                                                                                                                                                   |
| "why does ExecutionFactory have such a weird api?" | "look through ExecutionFactory's git history and summarize how its api came to be"                                                                                                                                                                                                                                                                     |
| "add a calendar widget"                            | "look at how existing widgets are implemented on the home page to understand the patterns and specifically how code and interfaces are separated out. HotDogWidget.php is a good example to start with. then, follow the pattern to implement a new calendar widget that lets the user select a month and paginate forwards/backwards to pick a year." |

#### **Visual Documentation**

- Include mockups, diagrams, and user flows
- Use screenshots and visual references
- Provide concrete examples over abstract descriptions

#### **Cross-functional Considerations**

Modern PRDs must address:

- **Support**: Documentation, training, processes
- **Growth & Data**: Tracking, metrics, A/B testing impact
- **Marketing**: Beta programs, onboarding, sales enablement
- **Enterprise**: Tier availability, activity logs, APIs
- **Platform**: API integration, mobile compatibility
- **Security & Privacy**: Data models, authentication, vendor flows

### **Collaboration Best Practices**

#### **Iterative Development**

1. Use AI for initial drafts and brainstorming
2. Human review and refinement of AI outputs
3. Stakeholder feedback integration
4. Continuous iteration based on implementation learnings

#### **Version Control & Decision Documentation**

- Maintain decision history and rationale
- Document controversial choices with tradeoff analysis
- Create templates for consistency across projects
- Use structured formats that both humans and AI can parse

## Emerging Trends: Prompt Requirements Documents

### **The "Vibe Coding" Era**

A new concept is emerging where traditional PRDs evolve into **Prompt Requirements Documents** - structured documentation optimized for AI-human collaboration in development workflows.

### **Key Characteristics of Prompt PRDs**

- **Structured Prompts**: Text, images, videos in machine-parseable formats
- **Workflow Integration**: Built into development tools (GitHub, Claude Code, Cursor)
- **Real-time Collaboration**: AI and humans working together on requirements
- **Context Management**: Handling AI context window limitations
- **Quality Prompts**: Focus on generating effective AI instructions

### **Implementation Workflow**

1. **Initial Setup**: Define rules and project overview
2. **Requirements Design**: Clarify features with AI collaboration
3. **Prompt Refinement**: Convert features to machine-friendly instructions
4. **Implementation**: Co-create code with AI verification
5. **Refactoring**: Improve quality and maintain coherence
6. **PRD Updates**: Integrate lessons learned back into documentation

## Claude Code Integration

### **CLAUDE.md Files for Project Context**

Modern AI-assisted development uses special `CLAUDE.md` files that AI automatically pulls into context:

```markdown
# Project Guide

## Development Workflow

- Always run `bin/verify` before submitting changes
- Pay attention to all warnings as they indicate potential issues

## Architecture

- Event sourcing with Commanded and EventStore
- Phoenix LiveView for real-time interfaces
- Oban for background jobs

## Code Style

- Use ES modules (import/export) syntax, not CommonJS
- Destructure imports when possible
- Query data at LiveView level, not in components
```

### **Custom Slash Commands**

Store prompt templates in `.claude/commands` folder for repeated workflows:

```markdown
Please analyze and fix the GitHub issue: $ARGUMENTS.

Follow these steps:

1. Use `gh issue view` to get the issue details
2. Understand the problem described in the issue
3. Search the codebase for relevant files
4. Implement the necessary changes to fix the issue
5. Write and run tests to verify the fix
6. Create a descriptive commit message
```

## Implementation Recommendations

### **For Traditional Teams**

1. Start with proven templates (Figma's approach)
2. Focus on clear problem statements and success metrics
3. Include comprehensive launch checklists
4. Maintain visual documentation and user flows

### **For AI-Assisted Teams**

1. Adopt hybrid approach combining traditional and AI-driven PRDs
2. Create structured `CLAUDE.md` files for project context
3. Develop custom slash commands for repeated workflows
4. Focus on prompt quality and iteration cycles

### **Universal Best Practices**

1. **Specificity**: Clear, detailed requirements over vague descriptions
2. **Visual Documentation**: Include mockups, diagrams, user flows
3. **Cross-functional Planning**: Address all stakeholder needs upfront
4. **Measurable Success**: Define concrete metrics and criteria
5. **Iterative Refinement**: Continuous improvement based on feedback
6. **Decision Documentation**: Track controversial choices and tradeoffs

## Tools & Resources

### **Traditional PRD Tools**

- Notion, Jira, Confluence
- Figma (design integration)
- Linear, Asana (project management)

### **AI-Assisted PRD Tools**

- ChatPRD (specialized AI assistant for product managers)
- Claude Code (agentic coding with context files)
- Cursor (AI-powered IDE with rules files)
- GitHub (for Prompt PRD version control)

### **Key Features to Look For**

- **Affordable Pricing**: Tools starting at $5/month
- **Product Manager Focus**: Purpose-built vs. generic AI tools
- **Template Libraries**: Pre-built structures and examples
- **Collaboration Features**: Team sharing and feedback cycles
- **Integration Capabilities**: Works with existing development workflows

## Conclusion

The evolution from traditional PRDs to AI-assisted and Prompt Requirements Documents reflects the broader shift toward human-AI collaboration in product development. Success requires balancing proven documentation practices with emerging AI workflow optimization techniques.

The key is to maintain the core value of PRDs - stakeholder alignment and clear requirements - while leveraging AI to improve quality, speed, and consistency of documentation and implementation.
