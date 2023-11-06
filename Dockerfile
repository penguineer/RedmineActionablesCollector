FROM alpine/git AS install

# If the --dirty flag is left out, only the .git directory has to be copied
ADD . /git/
RUN git describe --always --dirty > /git-version.txt


FROM python:3.12

EXPOSE 8080
HEALTHCHECK --interval=10s CMD curl --fail http://localhost:8080/v0/health || exit 1

COPY src/OAS3.yml /

COPY requirements.txt /
RUN pip install -r requirements.txt

COPY src/*.py /

COPY --from=install /git-version.txt /

CMD ["python", "-u", "./app.py"]
