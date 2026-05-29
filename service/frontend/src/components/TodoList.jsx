import React from 'react';

/**
 * TodoList component displays a list of tasks with their completion status.
 *
 * @param {Object} props
 * @param {Array} props.todos - Array of todo objects with id, task, and status properties
 */
export function TodoList({ todos }) {
  if (!todos || todos.length === 0) return null;

  const completedCount = todos.filter(t => t.status === 'complete').length;

  return (
    <div className="todo-list">
      <div className="todo-header">
        <span className="todo-title">Progress</span>
        <span className="todo-count">
          {completedCount} / {todos.length}
        </span>
      </div>

      <div className="todo-items">
        {todos.map(todo => (
          <div key={todo.id} className={`todo-item ${todo.status}`}>
            <div className="todo-checkbox">
              {todo.status === 'complete' && (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M13.488 3.688l-7.86 7.86-3.25-3.25-1.061 1.06 4.311 4.312L14.548 4.75z"/>
                </svg>
              )}
            </div>
            <span className="todo-text">{todo.task}</span>
            {todo.status === 'in_progress' && (
              <div className="todo-spinner">
                <div className="spinner" />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
