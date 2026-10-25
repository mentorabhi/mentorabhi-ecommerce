# syntax=docker/dockerfile:1@sha256:4edf897a3ffa55b89f906fc8cc78afdb3f1834cc9c7083565e611a8a7d5fe99e
ARG BUILD_IMAGE
ARG JAVA_IMAGE
FROM ${BUILD_IMAGE} AS build
ARG SERVICE_NAME
ARG SKIP_TESTS=false
WORKDIR /workspace
COPY services/${SERVICE_NAME}/pom.xml ./pom.xml
COPY services/${SERVICE_NAME}/src ./src
RUN --mount=type=cache,id=supersports-maven,target=/root/.m2,sharing=locked mvn -B -ntp verify -DskipTests="${SKIP_TESTS}"

FROM scratch AS telemetry-agent
ADD --checksum=sha256:5f9d1f10056ed2b246fbb19543519b8066cda23d6aff19022dbdb84402d6c3ab https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/download/v2.33.0/opentelemetry-javaagent.jar /opentelemetry-javaagent.jar

FROM ${JAVA_IMAGE}
ARG SERVICE_NAME
ARG RELEASE_VERSION
LABEL org.opencontainers.image.title="SuperSports ${SERVICE_NAME}" \
      org.opencontainers.image.version="${RELEASE_VERSION}"
WORKDIR /app
COPY --from=build --chown=10001:10001 /workspace/target/*.jar /app/app.jar
COPY --from=telemetry-agent --chown=10001:10001 /opentelemetry-javaagent.jar /app/opentelemetry-javaagent.jar
ENV OTEL_SERVICE_NAME=${SERVICE_NAME} \
    OTEL_SDK_DISABLED=true
COPY --chown=10001:10001 devops/docker/healthcheck.sh /app/healthcheck.sh
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=12 CMD ["bash", "/app/healthcheck.sh"]
ENTRYPOINT ["java", "-javaagent:/app/opentelemetry-javaagent.jar", "-jar", "/app/app.jar"]
