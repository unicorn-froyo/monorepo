FROM ruby:3.4-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends --yes build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=app_context third_party/ruby/Gemfile third_party/ruby/Gemfile.lock ./
RUN bundle config set without "development test" \
    && bundle install --jobs 4 \
    && rm -rf /usr/local/bundle/cache

COPY --from=app_context src /app/src

ENV RAILS_ENV=production
USER 65532:65532
EXPOSE 8080

CMD ["bundle", "exec", "puma", "--port", "8080", "src/apis/examples/ruby/config.ru"]
