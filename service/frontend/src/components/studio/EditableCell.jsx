export default function EditableCell({ value, editing, draft, onStartEdit, onDraftChange, onKeyDown, onBlur }) {
  if (editing) {
    return (
      <input
        className="studio-workspace-edit-input"
        value={draft}
        onChange={(e) => onDraftChange(e.target.value)}
        onKeyDown={onKeyDown}
        onBlur={onBlur}
        autoFocus
      />
    );
  }
  return (
    <span className="studio-workspace-editable-cell" onClick={onStartEdit}>
      {value || '-'}
    </span>
  );
}
