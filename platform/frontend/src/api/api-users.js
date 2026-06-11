export const getUsers = async () => {
  const response = await apiFetch(`${USERS_API}/users`);
  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Failed to load user list'));
  }
  return response.json();
};

export const updateUser = async (userId, userData) => {
  const response = await apiFetch(`${USERS_API}/users/${userId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userData),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Failed to update user'));
  }
  return response.json();
};

export const deleteUser = async (userId) => {
  const response = await apiFetch(`${USERS_API}/users/${userId}`, {
    method: 'DELETE',
  });
  if (!response.ok && response.status !== 204) {
    throw new Error(await parseApiError(response, 'Failed to delete user'));
  }
};

// Regression
const saveAsRegression = async (testId, runId) => {
  const response = await apiFetch(`${TEST_API}/test-definitions/regression/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ run_id: runId })
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Failed to save regression test'));
  }
  return response.json();
};

const getRegressionTests = async () => {
  const response = await apiFetch(`${TEST_API}/test-definitions/regression`);
  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Failed to load regression test list'));
  }
  return response.json();
};

