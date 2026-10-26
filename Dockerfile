FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY core/ core/
COPY tests/ tests/
COPY tools/ tools/
COPY demo.py app.py conftest.py ./
RUN python demo.py && python tools/verify_dxf.py out/plan.dxf > /tmp/verify.json \
    && pytest tests/ -q
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8090"]
