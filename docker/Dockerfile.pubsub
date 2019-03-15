FROM google/cloud-sdk:237.0.0-alpine

# Install Java and a pubsub-emulator
RUN apk --update add openjdk8-jre
RUN gcloud components install pubsub-emulator beta --quiet

# Copy the run script
COPY docker/run_pubsub.sh /tmp

EXPOSE 5010

CMD /tmp/run_pubsub.sh
