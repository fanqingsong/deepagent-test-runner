import { useState, useEffect, useCallback } from 'react';
import {
  getBudgets,
  getBudget,
  createBudget,
  updateBudget,
  deleteBudget,
  getBudgetHierarchy,
} from '../../api/api-token';
import AlertBanner from '../AlertBanner';
import Modal from '../Modal';
import './BudgetManagement.css';

const STATUS_LABELS = {
  active: 'Active',
  warning: 'Warning',
  exhausted: 'Exhausted',
  pending: 'Pending',
  archived: 'Archived',
};

const SCOPE_LABELS = {
  global: 'Global',
  organization: 'Organization',
  team: 'Team',
  user: 'User',
  project: 'Project',
};

function formatNumber(num) {
  if (!num && num !== 0) return '0';
  return num.toLocaleString();
}

function formatPercentage(value, total) {
  if (!total || total === 0) return '0%';
  return `${Math.round((value / total) * 100)}%`;
}

// Status Badge Component
function StatusBadge({ status }) {
  return <span className={`status-badge ${status}`}>{STATUS_LABELS[status] || status}</span>;
}

// Filter Bar Component
function FilterBar({ filters, onFilterChange, onSearch, onCreate }) {
  return (
    <div className="filter-bar">
      <div className="filter-group">
        <input
          type="text"
          placeholder="Search budgets..."
          className="search-input"
          value={filters.search || ''}
          onChange={(e) => onSearch(e.target.value)}
        />
      </div>
      <div className="filter-group">
        <select
          className="filter-select"
          value={filters.status || 'all'}
          onChange={(e) => onFilterChange('status', e.target.value)}
        >
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="warning">Warning</option>
          <option value="exhausted">Exhausted</option>
          <option value="archived">Archived</option>
        </select>
      </div>
      <div className="filter-group">
        <select
          className="filter-select"
          value={filters.scope || 'all'}
          onChange={(e) => onFilterChange('scope', e.target.value)}
        >
          <option value="all">All Scopes</option>
          <option value="global">Global</option>
          <option value="organization">Organization</option>
          <option value="team">Team</option>
          <option value="user">User</option>
          <option value="project">Project</option>
        </select>
      </div>
      <button className="create-button" onClick={onCreate}>
        + New Budget
      </button>
    </div>
  );
}

// Budget Table Component
function BudgetTable({ budgets, onEdit, onDelete, onView }) {
  return (
    <div className="budget-table-container">
      <table className="budget-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Scope</th>
            <th>Limit</th>
            <th>Used</th>
            <th>Utilization</th>
            <th>Period</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {budgets.map((budget) => (
            <tr key={budget.id}>
              <td className="budget-name">{budget.name}</td>
              <td>
                <span className="scope-badge">{SCOPE_LABELS[budget.scope] || budget.scope}</span>
              </td>
              <td>{formatNumber(budget.limit)} tokens</td>
              <td>{formatNumber(budget.used)} tokens</td>
              <td>
                <div className="utilization-bar">
                  <div
                    className={`utilization-fill ${
                      budget.utilization_percent >= 90
                        ? 'critical'
                        : budget.utilization_percent >= 75
                        ? 'warning'
                        : 'normal'
                    }`}
                    style={{ width: `${Math.min(100, budget.utilization_percent || 0)}%` }}
                  />
                  <span className="utilization-text">
                    {formatPercentage(budget.used, budget.limit)}
                  </span>
                </div>
              </td>
              <td>{budget.period}</td>
              <td>
                <StatusBadge status={budget.status} />
              </td>
              <td className="budget-actions">
                <button
                  className="action-button"
                  onClick={() => onView(budget)}
                  title="View details"
                >
                  View
                </button>
                <button
                  className="action-button"
                  onClick={() => onEdit(budget)}
                  title="Edit budget"
                >
                  Edit
                </button>
                <button
                  className="action-button danger"
                  onClick={() => onDelete(budget)}
                  title="Delete budget"
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Budget Form Component
function BudgetForm({ budget, onSave, onCancel, onSubmit }) {
  const [formData, setFormData] = useState({
    name: budget?.name || '',
    scope: budget?.scope || 'user',
    scope_id: budget?.scope_id || '',
    limit: budget?.limit || 100000,
    period: budget?.period || 'monthly',
    alert_threshold: budget?.alert_threshold || 80,
    description: budget?.description || '',
    parent_id: budget?.parent_id || '',
    status: budget?.status || 'active',
  });

  const [errors, setErrors] = useState({});

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Clear error for this field
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: null }));
    }
  };

  const validate = () => {
    const newErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    }
    if (!formData.limit || formData.limit <= 0) {
      newErrors.limit = 'Limit must be greater than 0';
    }
    if (!formData.scope_id && formData.scope !== 'global') {
      newErrors.scope_id = 'Scope ID is required for this scope';
    }
    if (formData.alert_threshold < 0 || formData.alert_threshold > 100) {
      newErrors.alert_threshold = 'Alert threshold must be between 0 and 100';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    if (validate()) {
      onSubmit(formData);
    }
  };

  return (
    <form className="budget-form" onSubmit={handleSubmit}>
      <div className="form-group">
        <label className="form-label">Name *</label>
        <input
          type="text"
          className={`form-input ${errors.name ? 'error' : ''}`}
          value={formData.name}
          onChange={(e) => handleChange('name', e.target.value)}
          placeholder="Enter budget name"
        />
        {errors.name && <span className="form-error">{errors.name}</span>}
      </div>

      <div className="form-row">
        <div className="form-group">
          <label className="form-label">Scope *</label>
          <select
            className="form-select"
            value={formData.scope}
            onChange={(e) => handleChange('scope', e.target.value)}
          >
            <option value="global">Global</option>
            <option value="organization">Organization</option>
            <option value="team">Team</option>
            <option value="user">User</option>
            <option value="project">Project</option>
          </select>
        </div>

        {formData.scope !== 'global' && (
          <div className="form-group">
            <label className="form-label">Scope ID *</label>
            <input
              type="text"
              className={`form-input ${errors.scope_id ? 'error' : ''}`}
              value={formData.scope_id}
              onChange={(e) => handleChange('scope_id', e.target.value)}
              placeholder="Enter scope ID"
            />
            {errors.scope_id && <span className="form-error">{errors.scope_id}</span>}
          </div>
        )}
      </div>

      <div className="form-row">
        <div className="form-group">
          <label className="form-label">Token Limit *</label>
          <input
            type="number"
            className={`form-input ${errors.limit ? 'error' : ''}`}
            value={formData.limit}
            onChange={(e) => handleChange('limit', parseInt(e.target.value) || 0)}
            min="0"
          />
          {errors.limit && <span className="form-error">{errors.limit}</span>}
        </div>

        <div className="form-group">
          <label className="form-label">Period *</label>
          <select
            className="form-select"
            value={formData.period}
            onChange={(e) => handleChange('period', e.target.value)}
          >
            <option value="hourly">Hourly</option>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>
      </div>

      <div className="form-group">
        <label className="form-label">Alert Threshold (%)</label>
        <input
          type="number"
          className={`form-input ${errors.alert_threshold ? 'error' : ''}`}
          value={formData.alert_threshold}
          onChange={(e) => handleChange('alert_threshold', parseInt(e.target.value) || 0)}
          min="0"
          max="100"
        />
        {errors.alert_threshold && <span className="form-error">{errors.alert_threshold}</span>}
      </div>

      <div className="form-group">
        <label className="form-label">Description</label>
        <textarea
          className="form-textarea"
          value={formData.description}
          onChange={(e) => handleChange('description', e.target.value)}
          placeholder="Enter budget description"
          rows={3}
        />
      </div>

      <div className="form-group">
        <label className="form-label">Parent Budget</label>
        <input
          type="text"
          className="form-input"
          value={formData.parent_id}
          onChange={(e) => handleChange('parent_id', e.target.value)}
          placeholder="Enter parent budget ID"
        />
      </div>

      <div className="form-actions">
        <button type="button" className="cancel-button" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="submit-button">
          {budget?.id ? 'Update Budget' : 'Create Budget'}
        </button>
      </div>
    </form>
  );
}

// Budget Details Component
function BudgetDetails({ budget, onClose }) {
  if (!budget) return null;

  return (
    <div className="budget-details">
      <div className="details-header">
        <h3 className="details-title">{budget.name}</h3>
        <StatusBadge status={budget.status} />
      </div>

      <div className="details-grid">
        <div className="detail-item">
          <span className="detail-label">Scope</span>
          <span className="detail-value">{SCOPE_LABELS[budget.scope] || budget.scope}</span>
        </div>
        <div className="detail-item">
          <span className="detail-label">Limit</span>
          <span className="detail-value">{formatNumber(budget.limit)} tokens</span>
        </div>
        <div className="detail-item">
          <span className="detail-label">Used</span>
          <span className="detail-value">{formatNumber(budget.used)} tokens</span>
        </div>
        <div className="detail-item">
          <span className="detail-label">Utilization</span>
          <span className="detail-value">{formatPercentage(budget.used, budget.limit)}</span>
        </div>
        <div className="detail-item">
          <span className="detail-label">Period</span>
          <span className="detail-value">{budget.period}</span>
        </div>
        <div className="detail-item">
          <span className="detail-label">Alert Threshold</span>
          <span className="detail-value">{budget.alert_threshold}%</span>
        </div>
        <div className="detail-item full-width">
          <span className="detail-label">Description</span>
          <span className="detail-value">{budget.description || 'No description provided'}</span>
        </div>
        <div className="detail-item">
          <span className="detail-label">Created</span>
          <span className="detail-value">
            {new Date(budget.created_at).toLocaleDateString()}
          </span>
        </div>
        <div className="detail-item">
          <span className="detail-label">Updated</span>
          <span className="detail-value">
            {new Date(budget.updated_at).toLocaleDateString()}
          </span>
        </div>
      </div>

      <div className="details-actions">
        <button className="close-button" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}

// Delete Confirmation Component
function DeleteConfirmation({ budget, onConfirm, onCancel }) {
  return (
    <div className="delete-confirmation">
      <h3 className="confirmation-title">Delete Budget</h3>
      <p className="confirmation-message">
        Are you sure you want to delete the budget "{budget?.name}"? This action cannot be undone.
      </p>
      <div className="confirmation-actions">
        <button className="cancel-button" onClick={onCancel}>
          Cancel
        </button>
        <button className="danger-button" onClick={onConfirm}>
          Delete Budget
        </button>
      </div>
    </div>
  );
}

// Main Budget Management Component
function BudgetManagement() {
  const [budgets, setBudgets] = useState([]);
  const [filteredBudgets, setFilteredBudgets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({ status: 'all', scope: 'all', search: '' });
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [selectedBudget, setSelectedBudget] = useState(null);

  const fetchBudgets = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await getBudgets();
      setBudgets(data.budgets || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBudgets();
  }, [fetchBudgets]);

  useEffect(() => {
    let filtered = budgets;

    // Filter by status
    if (filters.status !== 'all') {
      filtered = filtered.filter((b) => b.status === filters.status);
    }

    // Filter by scope
    if (filters.scope !== 'all') {
      filtered = filtered.filter((b) => b.scope === filters.scope);
    }

    // Filter by search
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      filtered = filtered.filter(
        (b) =>
          b.name.toLowerCase().includes(searchLower) ||
          b.description?.toLowerCase().includes(searchLower)
      );
    }

    setFilteredBudgets(filtered);
  }, [budgets, filters]);

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleSearch = (value) => {
    setFilters((prev) => ({ ...prev, search: value }));
  };

  const handleCreate = async (formData) => {
    try {
      await createBudget(formData);
      setShowCreateForm(false);
      await fetchBudgets();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleEdit = async (formData) => {
    try {
      await updateBudget(selectedBudget.id, formData);
      setShowEditForm(false);
      setSelectedBudget(null);
      await fetchBudgets();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async () => {
    try {
      await deleteBudget(selectedBudget.id);
      setShowDeleteConfirm(false);
      setSelectedBudget(null);
      await fetchBudgets();
    } catch (err) {
      setError(err.message);
    }
  };

  const openEditForm = (budget) => {
    setSelectedBudget(budget);
    setShowEditForm(true);
  };

  const openDeleteConfirm = (budget) => {
    setSelectedBudget(budget);
    setShowDeleteConfirm(true);
  };

  const openDetails = (budget) => {
    setSelectedBudget(budget);
    setShowDetails(true);
  };

  if (loading) {
    return (
      <div className="budget-management">
        <div className="loading-state">Loading budgets...</div>
      </div>
    );
  }

  return (
    <div className="budget-management">
      <div className="page-header">
        <h2 className="page-title">Budget Management</h2>
      </div>

      {error && (
        <AlertBanner
          message={`Error: ${error}`}
          type="error"
          onDismiss={() => setError(null)}
        />
      )}

      <FilterBar
        filters={filters}
        onFilterChange={handleFilterChange}
        onSearch={handleSearch}
        onCreate={() => setShowCreateForm(true)}
      />

      {filteredBudgets.length === 0 ? (
        <div className="empty-state">
          <p>No budgets found matching your filters.</p>
          <button className="create-button" onClick={() => setShowCreateForm(true)}>
            Create your first budget
          </button>
        </div>
      ) : (
        <BudgetTable
          budgets={filteredBudgets}
          onEdit={openEditForm}
          onDelete={openDeleteConfirm}
          onView={openDetails}
        />
      )}

      {/* Create Form Modal */}
      <Modal
        isOpen={showCreateForm}
        onClose={() => setShowCreateForm(false)}
        title="Create New Budget"
      >
        <BudgetForm
          budget={null}
          onSubmit={handleCreate}
          onCancel={() => setShowCreateForm(false)}
        />
      </Modal>

      {/* Edit Form Modal */}
      <Modal
        isOpen={showEditForm}
        onClose={() => {
          setShowEditForm(false);
          setSelectedBudget(null);
        }}
        title="Edit Budget"
      >
        <BudgetForm
          budget={selectedBudget}
          onSubmit={handleEdit}
          onCancel={() => {
            setShowEditForm(false);
            setSelectedBudget(null);
          }}
        />
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteConfirm}
        onClose={() => {
          setShowDeleteConfirm(false);
          setSelectedBudget(null);
        }}
        title="Delete Budget"
      >
        <DeleteConfirmation
          budget={selectedBudget}
          onConfirm={handleDelete}
          onCancel={() => {
            setShowDeleteConfirm(false);
            setSelectedBudget(null);
          }}
        />
      </Modal>

      {/* Details Modal */}
      <Modal
        isOpen={showDetails}
        onClose={() => {
          setShowDetails(false);
          setSelectedBudget(null);
        }}
        title="Budget Details"
      >
        <BudgetDetails
          budget={selectedBudget}
          onClose={() => {
            setShowDetails(false);
            setSelectedBudget(null);
          }}
        />
      </Modal>
    </div>
  );
}

export default BudgetManagement;
