/**
 * TodoList — real-time agent progress display.
 *
 * Reads a `todos` array from deep-agent state and renders each item
 * with status-based styling, a progress bar, and completion count.
 */
function normalizeStatus(todo) {
  if (todo.status) return todo.status;
  if (todo.completed) return 'completed';
  return 'pending';
}

const STATUS_CONFIG = {
  pending: {
    icon: '○',
    iconClass: 'todo-icon todo-icon--pending',
    itemClass: 'todo-item todo-item--pending',
  },
  in_progress: {
    icon: '◉',
    iconClass: 'todo-icon todo-icon--in_progress',
    itemClass: 'todo-item todo-item--in_progress',
  },
  completed: {
    icon: '✓',
    iconClass: 'todo-icon todo-icon--completed',
    itemClass: 'todo-item todo-item--completed',
  },
};

export function TodoList({ todos }) {
  if (!todos || todos.length === 0) return null;

  const completed = todos.filter((t) => normalizeStatus(t) === 'completed').length;
  const percentage = Math.round((completed / todos.length) * 100);

  return (
    <div className="todo-list-panel">
      <div className="todo-list-header">
        <span className="todo-list-title">Agent Progress</span>
        <span className="todo-list-count">{completed}/{todos.length} tasks</span>
      </div>

      <div className="todo-progress">
        <div className="todo-progress-labels">
          <span className="todo-progress-label">Progress</span>
          <span className="todo-progress-pct">{percentage}%</span>
        </div>
        <div className="todo-progress-track">
          <div
            className="todo-progress-fill"
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>

      <ul className="todo-items">
        {todos.map((todo, i) => {
          const status = normalizeStatus(todo);
          const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
          const text = todo.content || todo.title || String(todo);

          return (
            <li key={`todo-${i}`} className={cfg.itemClass}>
              <span className={cfg.iconClass}>{cfg.icon}</span>
              <span className="todo-text">{text}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
