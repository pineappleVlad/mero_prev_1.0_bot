FROM python

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y locales locales-all
RUN locale-gen ru_RU.UTF-8
ENV LC_TIME ru_RU.UTF-8

COPY . .

CMD ["python", "bot.py"]
