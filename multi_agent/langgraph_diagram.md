# LangGraph Framework Flow

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	Trigger\20Phase\201\a\5bAgent\204\5d(Trigger Phase 1
[Agent 4])
	Ask\20For\20Template\3f\a\5bAgent\202\5d(Ask For Template?
[Agent 2])
	Create\20Evaluation\20Template\a\5bAgent\201\5d(Create Evaluation Template
[Agent 1])
	Draft\20Guidelines\20\26\20Constraints\a\5bAgent\202\5d(Draft Guidelines & Constraints
[Agent 2])
	Refine\20Guidelines\20\26\20Constraints\20\28Checker\29\a\5bAgent\202\5d(Refine Guidelines & Constraints (Checker)
[Agent 2])
	Answer\20Syntax\20Questions\a\5bAgent\201\5d(Answer Syntax Questions
[Agent 1])
	Receive\20Guidelines\20Constraints\a\5bAgent\204\5d(Receive Guidelines Constraints
[Agent 4])
	__end__([<p>__end__</p>]):::last
	Answer\20Syntax\20Questions\a\5bAgent\201\5d --> Refine\20Guidelines\20\26\20Constraints\20\28Checker\29\a\5bAgent\202\5d;
	Ask\20For\20Template\3f\a\5bAgent\202\5d -. &nbsp;create_evaluation_template&nbsp; .-> Create\20Evaluation\20Template\a\5bAgent\201\5d;
	Ask\20For\20Template\3f\a\5bAgent\202\5d -. &nbsp;draft_guidelines_constraints&nbsp; .-> Draft\20Guidelines\20\26\20Constraints\a\5bAgent\202\5d;
	Create\20Evaluation\20Template\a\5bAgent\201\5d --> Draft\20Guidelines\20\26\20Constraints\a\5bAgent\202\5d;
	Draft\20Guidelines\20\26\20Constraints\a\5bAgent\202\5d --> Refine\20Guidelines\20\26\20Constraints\20\28Checker\29\a\5bAgent\202\5d;
	Refine\20Guidelines\20\26\20Constraints\20\28Checker\29\a\5bAgent\202\5d -. &nbsp;answer_syntax_questions&nbsp; .-> Answer\20Syntax\20Questions\a\5bAgent\201\5d;
	Refine\20Guidelines\20\26\20Constraints\20\28Checker\29\a\5bAgent\202\5d -. &nbsp;draft_guidelines&nbsp; .-> Draft\20Guidelines\20\26\20Constraints\a\5bAgent\202\5d;
	Refine\20Guidelines\20\26\20Constraints\20\28Checker\29\a\5bAgent\202\5d -. &nbsp;receive_guidelines&nbsp; .-> Receive\20Guidelines\20Constraints\a\5bAgent\204\5d;
	Trigger\20Phase\201\a\5bAgent\204\5d --> Ask\20For\20Template\3f\a\5bAgent\202\5d;
	__start__ --> Trigger\20Phase\201\a\5bAgent\204\5d;
	Receive\20Guidelines\20Constraints\a\5bAgent\204\5d --> __end__;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc

```
