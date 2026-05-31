/**
 * PasswordReset Page
 *
 * Page for requesting password reset email.
 */

import PasswordResetForm from '../components/auth/PasswordResetForm';

function PasswordReset() {
  const handleSuccess = (email) => {
    console.log('Password reset email sent to:', email);
  };

  const handleCancel = () => {
    window.location.href = '/login';
  };

  return (
    <div className="password-reset-page">
      <PasswordResetForm onSuccess={handleSuccess} onCancel={handleCancel} />
    </div>
  );
}

export default PasswordReset;
