---
name: market-research
description: Conduct structured competitive and market intelligence analysis with actionable SWOT synthesis.
---

# Market Research Skill

Use this skill when you are asked to analyze an industry, emerging technology, competitor landscape, or business opportunity.

## Process Workflow

1. **Information Gathering**:
   - Formulate targeted queries for search and data retrieval.
   - Use `serper_search` or domain tools to obtain up-to-date facts, market size, leading vendors, and customer friction points.
   - Verify timestamps and market context with `get_current_datetime`.

2. **Market Synthesis**:
   - **Market Overview**: Identify TAM (Total Addressable Market), growth rate (CAGR), and macroeconomic trends.
   - **Competitor Landscape**: Map primary players, market share leaders, and disruptive new entrants.
   - **Customer Demand & Pain Points**: Synthesize what customers currently struggle with.

3. **SWOT Framework**:
   - **Strengths**: Inherent advantages, moat, technological edge.
   - **Weaknesses**: Gaps, high cost structure, adoption barriers.
   - **Opportunities**: Unmet market segments, regulatory tailwinds, tech advancements.
   - **Threats**: Commoditization, incumbent retaliation, macroeconomic headwinds.

4. **Deliverable Generation**:
   - Save the finalized research report as a structured markdown file using `save_file_as_artifact`.
