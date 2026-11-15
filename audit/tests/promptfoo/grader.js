// Fake judge: behaviour selected by a marker anywhere in the grading prompt. No network.
module.exports = class Grader {
  id() { return 'fake-grader'; }
  async callApi(prompt) {
    if (prompt.includes('MODE_THROW')) throw new Error('simulated grader timeout');
    if (prompt.includes('MODE_ERROR')) return { error: 'API error: 503 grader unavailable' };
    if (prompt.includes('MODE_GARBAGE')) return { output: 'lol this is not json' };
    if (prompt.includes('MODE_REFUSE')) return { output: "I'm sorry, but I can't help with evaluating this content." };
    if (prompt.includes('MODE_OOR')) return { output: '{"score": 7, "reason": "no pass field, score out of [0,1]"}' };
    if (prompt.includes('MODE_FAILVERDICT')) return { output: '{"pass": false, "score": 0, "reason": "genuine fail"}' };
    return { output: '{"pass": true, "score": 1, "reason": "ok"}' };
  }
};
