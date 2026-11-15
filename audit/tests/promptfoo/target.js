// Fake target: behaviour selected by a marker in the prompt. No network.
module.exports = class Target {
  id() { return 'fake-target'; }
  async callApi(prompt) {
    if (prompt.includes('T_THROW')) throw new Error('simulated provider timeout (ETIMEDOUT)');
    if (prompt.includes('T_ERROR')) return { error: 'API error: 500 Internal Server Error' };
    if (prompt.includes('T_EMPTY')) return { output: '' };
    if (prompt.includes('T_NULL')) return {};
    if (prompt.includes('T_FILTER'))
      return { output: 'Content filtered by provider', isRefusal: true, finishReason: 'content_filter', guardrails: { flagged: true } };
    return { output: prompt };
  }
};
