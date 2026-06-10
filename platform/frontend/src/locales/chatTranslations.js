/**
 * Chat translations for English and Chinese.
 */

const chatTranslations = {
  en: {
    chatTitle: 'AI Assistant',
    chatWelcome: "Hello! I'm your AI assistant.",
    chatWelcomeHelp: 'I can help you:',
    chatHelpQuery: 'Query test cases and test suites',
    chatHelpUsers: 'View users and manage roles',
    chatHelpApprove: 'Approve or reject tests (requires permission)',
    chatHelpAnalytics: 'System analytics and metrics',
    chatHelpDataAnalysis: 'Data analysis and visualization',
    chatHelpKnowledge: 'Search knowledge base',
    chatHelpSql: 'SQL database queries',
    chatHelpEmail: 'Email operations',
    chatHelpContent: 'Content research and writing',
    chatHelpDeepResearch: 'Deep research on any topic',
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
    chatHelpUsers: '查看用户和管理角色',
    chatHelpApprove: '审批或驳回测试（需要权限）',
    chatHelpAnalytics: '系统统计分析和指标',
    chatHelpDataAnalysis: '数据分析和可视化',
    chatHelpKnowledge: '搜索知识库',
    chatHelpSql: 'SQL 数据库查询',
    chatHelpEmail: '邮件操作',
    chatHelpContent: '内容研究和撰写',
    chatHelpDeepResearch: '深度研究任意主题',
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
function getChatTranslation(key, language = 'en') {
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
