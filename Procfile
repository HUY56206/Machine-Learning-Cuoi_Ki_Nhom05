web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn ML_QSR.wsgi --bind 0.0.0.0:${PORT:-8000} --workers 1 --timeout 600
