import { useState, useEffect } from 'react';
import weatherClient from '../services/weather';

// Weather icon components following Carbon Design System
const SunIcon = ({ size = 48 }) => (
  <svg width={size} height={size} viewBox="0 0 32 32" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
    <path d="M16 4v2m0 20v2M8.34 8.34l1.41 1.41m11.9 11.9l1.41 1.41M4 16h2m20 0h2M8.34 23.66l1.41-1.41m11.9-11.9l1.41-1.41M16 12a4 4 0 1 0 0 8 4 4 0 0 0 0-8z"/>
  </svg>
);

const CloudIcon = ({ size = 48 }) => (
  <svg width={size} height={size} viewBox="0 0 32 32" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
    <path d="M24.5 13a4.5 4.5 0 0 0-4.2-2.9 5.4 5.4 0 0 0-5.1 3.6 3.5 3.5 0 0 0-2.7 1.4 3.7 3.7 0 0 0-1 2.5 3.7 3.7 0 0 0 3.7 3.7h9.3a4.5 4.5 0 0 0 0-9 4.2 4.2 0 0 0-.5.3z"/>
  </svg>
);

const RainIcon = ({ size = 48 }) => (
  <svg width={size} height={size} viewBox="0 0 32 32" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
    <path d="M24.5 13a4.5 4.5 0 0 0-4.2-2.9 5.4 5.4 0 0 0-5.1 3.6 3.5 3.5 0 0 0-2.7 1.4 3.7 3.7 0 0 0-1 2.5 3.7 3.7 0 0 0 3.7 3.7h9.3a4.5 4.5 0 0 0 0-9 4.2 4.2 0 0 0-.5.3zM10 28l2-4m-4 4l2-4m6 4l2-4"/>
  </svg>
);

const LoadingSpinner = () => (
  <div style={{
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '200px'
  }}>
    <div style={{
      width: '48px',
      height: '48px',
      border: '3px solid var(--cds-border-subtle, #e0e0e0)',
      borderTop: '3px solid var(--cds-button-primary, #0f62fe)',
      borderRadius: '50%',
      animation: 'spin 1s linear infinite'
    }} />
  </div>
);

function NanjingWeatherPage() {
  const [weatherData, setWeatherData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  // Fetch weather data from backend API
  useEffect(() => {
    const fetchWeatherData = async () => {
      setLoading(true);
      try {
        const data = await weatherClient.getNanjingWeather();
        setWeatherData(data);
        setLastUpdate(new Date());
        setError(null);
      } catch (err) {
        setError('获取天气数据失败，请稍后重试');
        console.error('Weather fetch error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchWeatherData();

    // Refresh every 10 minutes
    const interval = setInterval(fetchWeatherData, 10 * 60 * 1000);

    return () => clearInterval(interval);
  }, []);

  const getWeatherIcon = (iconType) => {
    switch (iconType) {
      case 'sun':
        return <SunIcon />;
      case 'rain':
        return <RainIcon />;
      default:
        return <CloudIcon />;
    }
  };

  const getAQIColor = (aqi) => {
    if (aqi <= 50) return 'var(--cds-support-success, #24a148)';
    if (aqi <= 100) return 'var(--cds-support-warning, #f1c21b)';
    if (aqi <= 150) return '#ff8300';
    return 'var(--cds-support-error, #da1e28)';
  };

  const getUVLevel = (uvIndex) => {
    if (uvIndex <= 2) return { level: '低', color: 'var(--cds-support-success, #24a148)' };
    if (uvIndex <= 5) return { level: '中', color: '#ff8300' };
    if (uvIndex <= 7) return { level: '高', color: 'var(--cds-support-warning, #f1c21b)' };
    return { level: '很高', color: 'var(--cds-support-error, #da1e28)' };
  };

  const handleRefresh = () => {
    setLastUpdate(null);
    setWeatherData(null);
    // Trigger refetch by re-mounting the effect
    window.location.reload();
  };

  if (loading) {
    return (
      <div style={{
        padding: 'var(--cds-layout-sm)',
        background: 'var(--cds-background)',
        minHeight: 'calc(100vh - 48px)'
      }}>
        <LoadingSpinner />
        <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        padding: 'var(--cds-layout-sm)',
        background: 'var(--cds-background)',
        minHeight: 'calc(100vh - 48px)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <div style={{
          background: '#fff',
          padding: '48px',
          maxWidth: '400px',
          width: '100%',
          textAlign: 'center',
          border: 'none'
        }}>
          <div style={{
            fontSize: '48px',
            marginBottom: '16px',
            color: 'var(--cds-support-error, #da1e28)'
          }}>
            ⚠
          </div>
          <h2 style={{
            fontWeight: 300,
            marginBottom: '16px',
            color: 'var(--cds-text-primary, #161616)'
          }}>
            天气数据获取失败
          </h2>
          <p style={{
            color: 'var(--cds-text-secondary, #525252)',
            marginBottom: '24px'
          }}>
            {error}
          </p>
          <button
            onClick={handleRefresh}
            style={{
              padding: '14px 16px',
              background: 'var(--cds-button-primary, #0f62fe)',
              color: '#fff',
              border: 'none',
              borderRadius: '0',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: 400,
              height: '48px',
              width: '100%'
            }}
          >
            重新加载
          </button>
        </div>
      </div>
    );
  }

  const uvInfo = getUVLevel(weatherData.uvIndex);

  return (
    <div style={{
      padding: 'var(--cds-layout-sm)',
      background: 'var(--cds-background)',
      minHeight: 'calc(100vh - 48px)'
    }}>
      {/* Page Header */}
      <div style={{
        marginBottom: 'var(--cds-layout-md)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div>
          <h1 style={{
            fontSize: 'var(--cds-heading-01, 42px)',
            fontWeight: 'var(--cds-font-weight-light, 300)',
            lineHeight: 'var(--cds-display-line-height, 1.19)',
            marginBottom: '8px',
            color: 'var(--cds-text-primary, #161616)'
          }}>
            {weatherData.city} 天气
          </h1>
          <p style={{
            fontSize: 'var(--cds-body-short-01, 14px)',
            color: 'var(--cds-text-secondary, #525252)',
            letterSpacing: '0.16px',
            lineHeight: 'var(--cds-body-short-line-height, 1.29)'
          }}>
            {weatherData.cityEn} Weather Information
          </p>
        </div>
        {lastUpdate && (
          <button
            onClick={handleRefresh}
            style={{
              padding: '14px 16px',
              background: 'transparent',
              color: 'var(--cds-link-primary, #0f62fe)',
              border: 'none',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: 400,
              height: '48px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            ↻ 更新
          </button>
        )}
      </div>

      {/* Current Weather Card */}
      <div style={{
        background: 'var(--cds-layer-01, #f4f4f4)',
        padding: 'var(--cds-layout-md)',
        marginBottom: '16px',
        border: 'none',
        borderRadius: '0'
      }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '32px'
        }}>
          {/* Temperature Section */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '24px'
          }}>
            <div style={{ color: 'var(--cds-support-info, #0f62fe)' }}>
              {getWeatherIcon('sun')}
            </div>
            <div>
              <div style={{
                fontSize: '72px',
                fontWeight: 'var(--cds-font-weight-light, 300)',
                lineHeight: '1',
                color: 'var(--cds-text-primary, #161616)'
              }}>
                {weatherData.temperature}°
              </div>
              <div style={{
                fontSize: 'var(--cds-body-long-01, 16px)',
                color: 'var(--cds-text-secondary, #525252)',
                marginTop: '8px'
              }}>
                体感 {weatherData.feelsLike}° · {weatherData.weather}
              </div>
            </div>
          </div>

          {/* Details Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: '16px 32px'
          }}>
            <div>
              <div style={{
                fontSize: 'var(--cds-caption-01, 12px)',
                color: 'var(--cds-text-secondary, #525252)',
                letterSpacing: '0.32px',
                marginBottom: '4px'
              }}>
                湿度
              </div>
              <div style={{
                fontSize: 'var(--cds-heading-05, 20px)',
                fontWeight: 'var(--cds-font-weight-regular, 400)',
                color: 'var(--cds-text-primary, #161616)'
              }}>
                {weatherData.humidity}%
              </div>
            </div>

            <div>
              <div style={{
                fontSize: 'var(--cds-caption-01, 12px)',
                color: 'var(--cds-text-secondary, #525252)',
                letterSpacing: '0.32px',
                marginBottom: '4px'
              }}>
                风速
              </div>
              <div style={{
                fontSize: 'var(--cds-heading-05, 20px)',
                fontWeight: 'var(--cds-font-weight-regular, 400)',
                color: 'var(--cds-text-primary, #161616)'
              }}>
                {weatherData.windSpeed} m/s
              </div>
              <div style={{
                fontSize: 'var(--cds-caption-01, 12px)',
                color: 'var(--cds-text-secondary, #525252)',
                marginTop: '2px'
              }}>
                {weatherData.windDirection}
              </div>
            </div>

            <div>
              <div style={{
                fontSize: 'var(--cds-caption-01, 12px)',
                color: 'var(--cds-text-secondary, #525252)',
                letterSpacing: '0.32px',
                marginBottom: '4px'
              }}>
                气压
              </div>
              <div style={{
                fontSize: 'var(--cds-heading-05, 20px)',
                fontWeight: 'var(--cds-font-weight-regular, 400)',
                color: 'var(--cds-text-primary, #161616)'
              }}>
                {weatherData.pressure} hPa
              </div>
            </div>

            <div>
              <div style={{
                fontSize: 'var(--cds-caption-01, 12px)',
                color: 'var(--cds-text-secondary, #525252)',
                letterSpacing: '0.32px',
                marginBottom: '4px'
              }}>
                能见度
              </div>
              <div style={{
                fontSize: 'var(--cds-heading-05, 20px)',
                fontWeight: 'var(--cds-font-weight-regular, 400)',
                color: 'var(--cds-text-primary, #161616)'
              }}>
                {weatherData.visibility} km
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Air Quality & UV Index */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: '16px',
        marginBottom: '16px'
      }}>
        {/* Air Quality */}
        <div style={{
          background: 'var(--cds-layer-01, #f4f4f4)',
          padding: 'var(--cds-layout-md)',
          border: 'none'
        }}>
          <h3 style={{
            fontSize: 'var(--cds-heading-04, 20px)',
            fontWeight: 'var(--cds-font-weight-semibold, 600)',
            marginBottom: '16px',
            color: 'var(--cds-text-primary, #161616)'
          }}>
            空气质量
          </h3>
          <div style={{
            display: 'flex',
            alignItems: 'baseline',
            gap: '8px',
            marginBottom: '8px'
          }}>
            <span style={{
              fontSize: '48px',
              fontWeight: 'var(--cds-font-weight-light, 300)',
              color: getAQIColor(weatherData.aqi),
              lineHeight: '1'
            }}>
              {weatherData.aqi}
            </span>
            <span style={{
              fontSize: 'var(--cds-heading-04, 20px)',
              color: getAQIColor(weatherData.aqi)
            }}>
              {weatherData.aqiLevel}
            </span>
          </div>
          <p style={{
            fontSize: 'var(--cds-body-short-01, 14px)',
            color: 'var(--cds-text-secondary, #525252)',
            margin: 0
          }}>
            AQI 指数
          </p>
        </div>

        {/* UV Index */}
        <div style={{
          background: 'var(--cds-layer-01, #f4f4f4)',
          padding: 'var(--cds-layout-md)',
          border: 'none'
        }}>
          <h3 style={{
            fontSize: 'var(--cds-heading-04, 20px)',
            fontWeight: 'var(--cds-font-weight-semibold, 600)',
            marginBottom: '16px',
            color: 'var(--cds-text-primary, #161616)'
          }}>
            紫外线指数
          </h3>
          <div style={{
            display: 'flex',
            alignItems: 'baseline',
            gap: '8px',
            marginBottom: '8px'
          }}>
            <span style={{
              fontSize: '48px',
              fontWeight: 'var(--cds-font-weight-light, 300)',
              color: uvInfo.color,
              lineHeight: '1'
            }}>
              {weatherData.uvIndex}
            </span>
            <span style={{
              fontSize: 'var(--cds-heading-04, 20px)',
              color: uvInfo.color
            }}>
              {uvInfo.level}
            </span>
          </div>
          <p style={{
            fontSize: 'var(--cds-body-short-01, 14px)',
            color: 'var(--cds-text-secondary, #525252)',
            margin: 0
          }}>
            UV Index
          </p>
        </div>
      </div>

      {/* 7-Day Forecast */}
      <div style={{
        background: 'var(--cds-layer-01, #f4f4f4)',
        padding: 'var(--cds-layout-md)',
        border: 'none'
      }}>
        <h3 style={{
          fontSize: 'var(--cds-heading-04, 20px)',
          fontWeight: 'var(--cds-font-weight-semibold, 600)',
          marginBottom: '24px',
          color: 'var(--cds-text-primary, #161616)'
        }}>
          7天预报
        </h3>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
          gap: '16px'
        }}>
          {weatherData.forecast.map((day, index) => (
            <div
              key={index}
              style={{
                textAlign: 'center',
                padding: '16px',
                background: index === 0 ? 'var(--cds-tag-blue, #edf5ff)' : 'transparent',
                borderRadius: '0'
              }}
            >
              <div style={{
                fontSize: 'var(--cds-body-short-02, 14px)',
                fontWeight: 'var(--cds-font-weight-semibold, 600)',
                color: 'var(--cds-text-primary, #161616)',
                marginBottom: '12px'
              }}>
                {day.day}
              </div>
              <div style={{
                color: 'var(--cds-support-info, #0f62fe)',
                marginBottom: '12px',
                display: 'flex',
                justifyContent: 'center'
              }}>
                {getWeatherIcon(day.icon)}
              </div>
              <div style={{
                fontSize: 'var(--cds-body-short-01, 14px)',
                color: 'var(--cds-text-primary, #161616)',
                marginBottom: '4px'
              }}>
                <span style={{
                  fontWeight: 'var(--cds-font-weight-regular, 400)'
                }}>
                  {day.high}°
                </span>
                <span style={{ color: 'var(--cds-text-secondary, #525252)', margin: '0 4px' }}>
                  /
                </span>
                <span style={{ color: 'var(--cds-text-secondary, #525252)' }}>
                  {day.low}°
                </span>
              </div>
              <div style={{
                fontSize: 'var(--cds-caption-01, 12px)',
                color: 'var(--cds-text-secondary, #525252)',
                letterSpacing: '0.16px'
              }}>
                {day.weather}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Last Update */}
      {lastUpdate && (
        <div style={{
          marginTop: '24px',
          textAlign: 'center',
          fontSize: 'var(--cds-caption-01, 12px)',
          color: 'var(--cds-text-secondary, #525252)',
          letterSpacing: '0.32px'
        }}>
          最后更新: {lastUpdate.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
        </div>
      )}
    </div>
  );
}

export default NanjingWeatherPage;
