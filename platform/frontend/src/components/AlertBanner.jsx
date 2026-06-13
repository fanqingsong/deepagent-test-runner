/**
 * Alert Banner Component
 *
 * Displays critical alerts at the top of the Dashboard.
 * Dismissible with optional cooldown.
 * Follows the IBM Carbon design system.
 */

import React, { useState, useCallback } from 'react';
import useMonitoring from '../hooks/useMonitoring';
import { useAuth } from '../contexts/AuthContext';
import './AlertBanner.css';

/**
 * AlertBanner Component
 *
 * Shows critical alerts that need attention:
 * - Displays the most recent critical alert
 * - Dismissible with a cooldown option
 * - Shows alert severity, title, and description
 */
function AlertBanner({ className = '', cooldownMinutes = 15 }) {
  const { isAuthenticated } = useAuth();

  const { alerts, acknowledgeAlert, activeAlertsCount } = useMonitoring({
    pollInterval: 60000, // 1 minute for banner
    enabled: isAuthenticated, // Only poll when authenticated
  });

  const [dismissedUntil, setDismissedUntil] = useState(null);
  const [showCooldown, setShowCooldown] = useState(false);

  // Filter for critical alerts only
  const criticalAlerts = alerts.filter(alert => alert.severity === 'critical');
  const alertToShow = criticalAlerts.length > 0 ? criticalAlerts[0] : null;

  // Check if banner is currently dismissed (in cooldown)
  const isDismissed = dismissedUntil && new Date() < new Date(dismissedUntil);

  // Handle dismiss with cooldown - must be before early return
  const handleDismiss = useCallback((withCooldown = false) => {
    if (!alertToShow) return;

    if (withCooldown) {
      const cooldownUntil = new Date();
      cooldownUntil.setMinutes(cooldownUntil.getMinutes() + cooldownMinutes);
      setDismissedUntil(cooldownUntil.toISOString());
      setShowCooldown(false);
    } else {
      setDismissedUntil(null);
    }

    // Also acknowledge the alert in the system
    acknowledgeAlert(alertToShow.id).catch(err => {
      console.error('Failed to acknowledge alert:', err);
    });
  }, [alertToShow, acknowledgeAlert, cooldownMinutes]);

  if (!alertToShow || isDismissed) {
    return null;
  }

  return (
    <div className={`alert-banner alert-banner-${alertToShow.severity} ${className}`}>
      <div className="alert-banner-content">
        <div className="alert-banner-icon">
          {alertToShow.severity === 'critical' && '🔴'}
          {alertToShow.severity === 'warning' && '⚠️'}
        </div>

        <div className="alert-banner-message">
          <div className="alert-banner-title">{alertToShow.title}</div>
          {alertToShow.description && (
            <div className="alert-banner-description">{alertToShow.description}</div>
          )}
          <div className="alert-banner-meta">
            <span className="alert-banner-type">{alertToShow.alert_type}</span>
            {' · '}
            <span className="alert-banner-time">
              {new Date(alertToShow.created_at).toLocaleString()}
            </span>
          </div>
        </div>
      </div>

      <div className="alert-banner-actions">
        <button
          className="alert-banner-cooldown-btn"
          onClick={() => setShowCooldown(true)}
          title={`Dismiss for ${cooldownMinutes} minutes`}
        >
          Snooze ({cooldownMinutes}m)
        </button>
        <button
          className="alert-banner-dismiss-btn"
          onClick={() => handleDismiss(false)}
          title="Acknowledge and dismiss"
        >
          Acknowledge
        </button>
      </div>

      {showCooldown && (
        <div className="alert-banner-confirm">
          <span>Snooze for {cooldownMinutes} minutes?</span>
          <button
            className="alert-banner-confirm-btn"
            onClick={() => handleDismiss(true)}
          >
            Yes
          </button>
          <button
            className="alert-banner-cancel-btn"
            onClick={() => setShowCooldown(false)}
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}

export default AlertBanner;
