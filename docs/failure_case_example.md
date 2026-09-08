# Failure Case 1 : Malformed JSON entry from LLM extraction

**Input:** Page 4 of Delhivery Q4 FY24 earnings presentation (fragmented
slide-style bullet text with footnote markers 1-6).

**Problem:** The model's raw JSON output included a stray empty string
`""` as one array element, sitting between two valid fact objects. This
is not a valid fact object and would crash naive parsing code that
assumes every array element has an `entity` field.

**Likely cause:** the source text has an isolated numeric footnote
marker ("2") right before the "Express Parcel" bullet, which may have
confused the model into emitting a malformed placeholder for it.

**How we handle it:** our parsing step validates each item in the facts
array and skips (with a logged warning) any item that isn't a proper
object with the expected fields, rather than crashing.

## Failure Case 2: Groq API rejects LLM output as invalid JSON

**Input:** Same fragmented "FY24 highlights" slide page, but with the
longer, stricter schema prompt (v2) instead of the loose v1 prompt.

**Problem:** Groq's own `response_format: json_object` validation
rejected the model's generation entirely — `groq.BadRequestError:
json_validate_failed`, with an empty `failed_generation` field. This
is a different failure mode than the first case: here, the API layer
itself refuses to return anything, rather than returning malformed
JSON that we could inspect.

**Likely cause:** the longer, more detailed system prompt (full schema
+ worked example) may have caused the model to produce output that
broke structurally partway through generation, on a smaller 20B model.

**How we handle it:** added retry logic around the extraction call —
on failure, retry up to N times; if all retries fail, return a
clearly-marked `{"facts": [], "extraction_failed": True}` result
instead of crashing the pipeline, so one bad page never takes down
the whole extraction run.