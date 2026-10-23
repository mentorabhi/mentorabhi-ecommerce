# syntax=docker/dockerfile:1@sha256:4edf897a3ffa55b89f906fc8cc78afdb3f1834cc9c7083565e611a8a7d5fe99e
ARG BUILD_IMAGE
ARG JAVA_IMAGE
FROM ${BUILD_IMAGE} AS build
ARG SERVICE_NAME
WORKDIR /workspace
COPY services/${SERVICE_NAME}/pom.xml ./pom.xml
COPY services/${SERVICE_NAME}/src ./src
RUN --mount=type=cache,id=supersports-maven,target=/root/.m2,sharing=locked mvn -B -ntp verify

FROM ${JAVA_IMAGE}
ARG SERVICE_NAME
ARG RELEASE_VERSION
LABEL org.opencontainers.image.title="SuperSports ${SERVICE_NAME}" \
      org.opencontainers.image.version="${RELEASE_VERSION}"
WORKDIR /app
COPY --from=build --chown=10001:10001 /workspace/target/*.jar /app/app.jar
COPY --chown=10001:10001 devops/docker/healthcheck.sh /app/healthcheck.sh
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=12 CMD ["bash", "/app/healthcheck.sh"]
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
