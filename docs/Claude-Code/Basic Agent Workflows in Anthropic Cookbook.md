---
title: 
source: https://raw.githubusercontent.com/anthropics/anthropic-cookbook/refs/heads/main/patterns/agents/basic_workflows.ipynb
author: 
published: 
created: 2025-07-31
description: 
tags:
  - clippings
  - agents
  - workflows
---

This notebook demonstrates three practical multi-LLM workflows that trade off cost or latency for potentially improved task performance. These patterns are foundational for building agent-based systems with LLMs.

## Core Workflows

### 1. Prompt-Chaining
**Concept**: Decomposes a complex task into sequential subtasks, where each step builds on previous results.

**Implementation**:
```python
def chain(input: str, prompts: List[str]) -> str:
    """Chain multiple LLM calls sequentially, passing results between steps."""
    result = input
    for i, prompt in enumerate(prompts, 1):
        print(f"\nStep {i}:")
        result = llm_call(f"{prompt}\nInput: {result}")
        print(result)
    return result
```

**Example Use Case**: Structured data extraction and formatting
1. Extract numerical values and metrics
2. Convert values to percentages
3. Sort by numerical value
4. Format as Markdown table

**Sample Execution**:
```
Input text:
Q3 Performance Summary:
Our customer satisfaction score rose to 92 points this quarter.
Revenue grew by 45% compared to last year.
Market share is now at 23% in our primary market.
Customer churn decreased to 5% from 8%.
New user acquisition cost is $43 per user.
Product adoption rate increased to 78%.
Employee satisfaction is at 87 points.
Operating margin improved to 34%.

Step 1:
92: customer satisfaction points
45%: revenue growth
23%: market share
5%: customer churn
8%: previous customer churn
$43: user acquisition cost
78%: product adoption rate
87: employee satisfaction points
34%: operating margin

Step 2:
92%: customer satisfaction
45%: revenue growth
23%: market share
5%: customer churn
8%: previous customer churn
43.0: user acquisition cost
78%: product adoption rate
87%: employee satisfaction
34%: operating margin

Step 3:
Here are the lines sorted in descending order by numerical value:

92%: customer satisfaction
87%: employee satisfaction
78%: product adoption rate
45%: revenue growth
43.0: user acquisition cost
34%: operating margin
23%: market share
8%: previous customer churn
5%: customer churn

Step 4:
| Metric | Value |
|:--|--:|
| Customer Satisfaction | 92% |
| Employee Satisfaction | 87% |
| Product Adoption Rate | 78% |
| Revenue Growth | 45% |
| User Acquisition Cost | 43.0 |
| Operating Margin | 34% |
| Market Share | 23% |
| Previous Customer Churn | 8% |
| Customer Churn | 5% |
```

### 2. Parallelization
**Concept**: Distributes independent subtasks across multiple LLMs for concurrent processing to reduce total latency.

**Implementation**:
```python
def parallel(prompt: str, inputs: List[str], n_workers: int = 3) -> List[str]:
    """Process multiple inputs concurrently with the same prompt."""
    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = [executor.submit(llm_call, f"{prompt}\nInput: {x}") for x in inputs]
        return [f.result() for f in futures]
```

**Example Use Case**: Stakeholder impact analysis
- Process multiple stakeholder groups simultaneously
- Each gets tailored analysis with the same prompt

**Sample Output Structure**:
```
MARKET IMPACT ANALYSIS FOR CUSTOMERS
==================================
HIGH PRIORITY IMPACTS
-------------------
1. Price Sensitivity
- Rising inflation and costs likely to reduce purchasing power
- Increased competition for value-oriented products
- Risk of trading down to lower-cost alternatives

Recommended Actions:
• Introduce tiered pricing options
• Develop value-focused product lines
• Create loyalty programs with price benefits
• Highlight total cost of ownership benefits

2. Technology Demands
- Accelerating tech advancement creating higher expectations
- Integration of AI and smart features becoming standard
- Mobile/digital-first experience requirements

Recommended Actions:
• Accelerate digital transformation initiatives
• Invest in user experience improvements
• Develop smart product features
• Provide tech education and support
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
```

---


### 3. Routing
**Concept**: Dynamically selects specialized LLM paths based on input characteristics.

**Implementation**:
```python
def route(input: str, routes: Dict[str, str]) -> str:
    """Route input to specialized prompt using content classification."""
    # First determine appropriate route using LLM
    print(f"\nAvailable routes: {list(routes.keys())}")
    selector_prompt = f"""
    Analyze the input and select the most appropriate support team from these options: {list(routes.keys())}
    First explain your reasoning, then provide your selection in XML format:
    
    <reasoning>
    Brief explanation of why this ticket should be routed to a specific team.
    Consider key terms, user intent, and urgency level.
    </reasoning>
    
    <selection>
    The chosen team name
    </selection>
    
    Input: {input}""".strip()
    
    route_response = llm_call(selector_prompt)
    reasoning = extract_xml(route_response, 'reasoning')
    route_key = extract_xml(route_response, 'selection').strip().lower()
    
    print("Routing Analysis:")
    print(reasoning)
    print(f"\nSelected route: {route_key}")
    
    # Process input with selected specialized prompt
    selected_prompt = routes[route_key]
    return llm_call(f"{selected_prompt}\nInput: {input}")
```

**Example Use Case**: Customer support ticket handling
- Classify tickets into billing, technical, account, or product issues
- Route to specialized agent with appropriate context

**Sample Routing Process**:
```
Available routes: ['billing', 'technical', 'account', 'product']
Routing Analysis:
This issue is clearly related to account access and authentication problems. The user is experiencing login difficulties with their password, which is a core account security and access issue...

Selected route: account
Account Support Response:
Dear John,
I understand your urgency regarding account access. Before proceeding with account recovery, we must verify your identity...

++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
```

## Implementation Tips for Production

### Error Handling & Fallbacks
```python
# Add robust route selection with fallback
route_key = extract_xml(route_response, 'selection').strip().lower()
if route_key not in routes:
    # Try once more with constrained prompt
    fallback_selector = f"Choose only one of: {list(routes.keys())}..."
    route_key = extract_xml(llm_call(fallback_selector), 'selection').strip().lower()
    if route_key not in routes:
        route_key = 'account'  # safe default
```

### Maintaining Input Order in Parallel Processing
```python
# Preserve input order when using ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=n_workers) as ex:
    futures = [(i, ex.submit(llm_call, f"{prompt}\nInput: {x}")) for i, x in enumerate(inputs)]
    out = [None] * len(inputs)
    for i, f in futures:
        out[i] = f.result()
```

### Constrained Routing Prompts
```python
# More robust selector prompt
"Return only XML. No text outside XML.\n"
"<reasoning>Briefly cite keywords and intent that justify the route.</reasoning>\n"
"<selection>billing|technical|account|product</selection>\n"
"Input: {input}"

# Fallback prompt for invalid selections
"Your previous selection was invalid. Choose only one of: {list(routes.keys())}.\n"
"Return only:\n<selection>CHOICE</selection>\nInput: {input}"
```

## Obsidian Integration Guide

### Template Structure for Agent Workflows
Create these templates in your `Templates/` directory:

#### Chain Workflow Template
```markdown
---
type: agent-workflow
workflow: chain
run_date: {{date}}
tags: [agents, prompt-chaining]
source_note: [[Basic Agent Workflows in Anthropic Cookbook]]
---

**Input**
<paste text here>

**Prompts**
1. Extract pairs "value: metric" from the text.
2. Convert values to percentages where possible; otherwise keep numeric.
3. Sort descending by value.
4. Output a compact Markdown table: | Metric | Value |

**Code (Python)**
```python
result = chain(input_text, [
  "Extract 'value: metric' pairs...",
  "Convert values to percentages...",
  "Sort descending by numeric value...",
  "Format as Markdown table | Metric | Value |"
])
```

#### Routing Workflow Template
```markdown
---
type: agent-workflow
workflow: routing
run_date: {{date}}
tags: [agents, routing]
source_note: [[Basic Agent Workflows in Anthropic Cookbook]]
routes:
  - billing
  - technical
  - account
  - product
---

**Ticket**
Subject: …
Message: …

**Selector prompt**
Return only XML. No text outside XML.
<reasoning>Brief rationale.</reasoning>
<selection>billing|technical|account|product</selection>
Input: {{ticket}}

**Route prompts**
- billing: You are a billing support specialist… Input:
- technical: You are a technical support engineer… Input:
- account: You are an account security specialist… Input:
- product: You are a product specialist… Input:

**Code (Python)**
```python
response = route(ticket_text, support_routes)
```
```

### Dataview Integration
Track your agent workflow executions with Dataview:

```dataview
table run_date, tokens_used, cost_estimate, workflow
from "Agent Workflows"
sort run_date desc
```

### Best Practices
1. **Version Control**: Store your workflow templates in a dedicated directory
2. **Cost Tracking**: Add properties to track tokens used and API costs
3. **Error Logging**: Create a dedicated note for failed executions
4. **Prompt Evolution**: Maintain version history of your prompts
5. **Security**: Never store API keys in notes; use environment variables

These patterns provide a solid foundation for building agent-based workflows in your Obsidian vault. The key is to start simple with one workflow pattern, then gradually incorporate more complex routing and parallelization as your needs evolve.