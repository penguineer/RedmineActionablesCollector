FROM alpine/git AS install

# If the --dirty flag is left out, only the .git directory has to be copied
ADD . /git/
RUN git describe --always --dirty > /git-version.txt


FROM python:3.7

EXPOSE 8080

COPY src/OAS3.yml /

COPY requirements.txt /
RUN pip install -r requirements.txt

COPY src/*.py /

COPY --from=install /git-version.txt /

CMD ["python", "./app.py"]
