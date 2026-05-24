export default function EditableCell({ value, editing, draft, onStartEdit, onDraftChange, onKeyDown, onBlur }) {
  if (editing) {
    return (
      <input
        className="test-case-workspace-edit-input"
        value={draft}
        onChange={(e) => onDraftChange(e.target.value)}
        onKeyDown={onKeyDown}
        onBlur={onBlur}
        autoFocus
      />
    );
  }
  return (
    <span className="test-case-workspace-editable-cell" onClick={onStartEdit}>
      {value || '-'}
    </span>
  );
}
