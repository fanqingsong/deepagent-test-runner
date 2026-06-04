/**
 * Chat translations for English and Chinese.
 */

export const chatTranslations = {
  en: {
    chatTitle: 'AI Assistant',
    chatWelcome: "Hello! I'm your AI assistant.",
    chatWelcomeHelp: 'I can help you:',
    chatHelpQuery: 'Query test cases and test suites',
    chatHelpUsers: 'View users and roles',
    chatHelpRoles: 'Set user roles (requires permission)',
    chatHelpApprove: 'Approve test cases and test suites (requires permission)',
    clearButton: 'Clear',
    sendButton: 'Send',
    inputPlaceholder: 'Type your message...',
    thinking: 'Thinking...',
    connected: 'Connected',
    disconnected: 'Disconnected',
    errorPrefix: 'Sorry, I encountered an error',
    webSearchToggle: 'Web Search',
    deepThinkingToggle: 'Deep Thinking',
    subagentProgress: 'Subagent progress',
    subagentComplete: 'complete',
    subagentRunning: 'Running',
    subagentPending: 'Pending',
    subagentError: 'Error',
  },
  zh: {
    chatTitle: '智能助手',
    chatWelcome: '你好！我是你的智能助手。',
    chatWelcomeHelp: '我可以帮助你：',
    chatHelpQuery: '查询测试用例和测试套件',
    chatHelpUsers: '查看用户和角色信息',
    chatHelpRoles: '设置用户角色（需要权限）',
    chatHelpApprove: '审批测试用例和测试套件（需要权限）',
    clearButton: '清除',
    sendButton: '发送',
    inputPlaceholder: '输入你的消息...',
    thinking: '思考中...',
    connected: '已连接',
    disconnected: '未连接',
    errorPrefix: '抱歉，我遇到了错误',
    webSearchToggle: '联网搜索',
    deepThinkingToggle: '深度思考',
    subagentProgress: '子代理进度',
    subagentComplete: '完成',
    subagentRunning: '运行中',
    subagentPending: '等待中',
    subagentError: '错误',
  },
};

/**
 * Get translation for a key in the specified language.
 * @param {string} key - Translation key
 * @param {string} language - Language code ('en' or 'zh')
 * @returns {string} - Translated text
 */
export function getChatTranslation(key, language = 'en') {
  const translations = chatTranslations[language] || chatTranslations.en;
  return translations[key] || chatTranslations.en[key] || key;
}

/**
 * Hook for using chat translations.
 * @param {string} language - Language code
 * @returns {Object} - Translation functions
 */
export function useChatTranslations(language = 'en') {
  const t = (key) => getChatTranslation(key, language);

  return {
    t,
    language,
    isChinese: language === 'zh',
  };
}
