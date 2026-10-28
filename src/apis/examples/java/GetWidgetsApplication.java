package com.unicornfroyo.examples.widgets;

import com.unicornfroyo.api.AbstractApiBase;
import java.util.List;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication
public class GetWidgetsApplication extends AbstractApiBase {
  @RestController
  static class WidgetController {
    @GetMapping("/widgets")
    @ResponseStatus(HttpStatus.ACCEPTED)
    List<Object> widgets() {
      return List.of();
    }
  }
}
