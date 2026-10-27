# Glossary

| Term | Meaning |
|---|---|
| **Agent** | A program that uses an AI model to do a task. Here: review each requirement and report defects. |
| **Baseline (flag-everything)** | A deliberately dumb agent that flags every requirement for every defect. Any real agent should beat its score. |
| **Calibration** | Checking an AI grader against a human's grades on the same items before trusting it. |
| **Cohen's kappa** | Agreement between two graders, corrected for agreement expected by chance. 0 = chance, 1 = perfect, above 0.8 = strong. |
| **Context** | Extra text given to the model alongside the question. Here: the 3 most similar other requirements. |
| **Dev set** | The labeled requirements used while building and tuning the agent. |
| **Embedding** | A list of numbers that represents a text's meaning. Similar meanings get similar numbers. |
| **Evaluation harness** | The code that runs the agent and scores its output against the answer key. |
| **F1** | One score combining precision and recall. High only when both are high. |
| **False alarm / miss** | A flag on something that isn't a defect / a real defect the agent didn't flag. |
| **Gemma, Qwen, Granite, Kev** | The open AI models compared (from Google, Alibaba, IBM, and an open-source project built on Qwen). |
| **Average precision** | How well a model's probabilities rank real defects above clean ones, without picking a threshold. 1 = perfect ranking. |
| **Brier score** | How far stated probabilities are from what actually happened. 0 = perfect, 0.25 = coin flip. |
| **Ground truth / labels** | The answer key: which defects each requirement really has, decided by a person in advance. |
| **JSON schema** | A fixed data shape the model's answer must follow, like a typed API contract. |
| **LLM** | Large language model: the kind of AI model that reads and writes text. |
| **LLM-as-judge** | Using one AI model to grade another's output. Only trustworthy after calibration. |
| **n8n** | A workflow tool that chains steps (call model, query database) into a pipeline. The CI/CD of AI work. |
| **Ollama** | Software that runs AI models locally. |
| **Overfitting** | Scoring well on the data you tuned against and worse on new data. |
| **Precision** | Of everything the agent flagged, the share that was real. |
| **Prompt** | The instructions and input sent to the model. |
| **Qdrant** | A vector database: stores embeddings and finds the closest matches. |
| **Quantization (Q4_K_M)** | Storing a model at lower numeric precision (about 4 bits) so it fits on a consumer GPU. |
| **RAG** | Retrieval-augmented generation: look up relevant text first, then give it to the model as context. |
| **Recall** | Of all real defects, the share the agent caught. |
| **Retrieval** | Finding related text by meaning rather than keywords. |
| **Sealed test set** | Labeled data kept unused until the setup is final, then run once, to check the tuning carries over. |
| **Self-hosted** | Runs on your own hardware; no data goes to an outside service. |
| **System 1 model** | A decision model that returns calibrated probabilities for fixed questions in one fast pass, instead of writing text. Named after Kahneman's fast, intuitive "System 1" thinking. |
| **Mixture of experts (MoE)** | A large model that uses only a small part of itself per word (qwen3.6: 35B total, 3B active), so it runs faster than its size suggests. |
| **Threshold** | The probability above which a System 1 answer counts as a flag. Chosen on the dev set, then frozen. |
| **Temperature** | How random the model's output is. 0 = as repeatable as possible. |
| **8B, 35B** | Billions of parameters, a rough measure of model size. 8B models are small; 35B is mid-sized. |
