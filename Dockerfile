FROM alpine/git AS install

# If the --dirty flag is left out, only the .git directory has to be copied
ADD . /git/
RUN git describe --always --dirty > /git-version.txt


FROM python:3.7

EXPOSE 8080

ADD requirements.txt /
RUN pip install -r requirements.txt

ADD OAS3.yml /

ADD app.py /

COPY --from=install /git-version.txt /

CMD ["python", "./app.py"]
