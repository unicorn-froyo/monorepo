package com.unicornfroyo.examples.widgets;

import org.springframework.boot.SpringApplication;

/** Process entrypoint for the widgets service. */
public final class Server {
  private Server() {}

  public static void main(String[] args) {
    SpringApplication.run(GetWidgetsApplication.class, args);
  }
}
