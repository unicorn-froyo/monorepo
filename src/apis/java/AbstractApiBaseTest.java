package com.unicornfroyo.api;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.Test;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

public final class AbstractApiBaseTest {
  private final TestApplication application = new TestApplication();
  private final MockMvc mvc =
      MockMvcBuilders.standaloneSetup(new HealthController())
          .addFilters(application.securityHeadersFilter())
          .build();

  @Test
  public void hardensSuccessfulAndMissingHttpResponses() throws Exception {
    for (String path : new String[] {"/health", "/missing"}) {
      mvc.perform(get(path))
          .andExpect(header().string("X-Content-Type-Options", "nosniff"))
          .andExpect(header().string("X-Frame-Options", "DENY"))
          .andExpect(header().string("Referrer-Policy", "no-referrer"))
          .andExpect(
              header().string("Permissions-Policy", "camera=(), microphone=(), geolocation=()"))
          .andExpect(header().doesNotExist("Strict-Transport-Security"));
    }
  }

  @Test
  public void returnsTheConfiguredRoute() throws Exception {
    mvc.perform(get("/health")).andExpect(status().isNoContent());
  }

  @Test
  public void setsHstsForTrustedSecureRequests() throws Exception {
    mvc.perform(get("/missing").secure(true))
        .andExpect(header().string("Strict-Transport-Security", "max-age=31536000"));
  }

  static class TestApplication extends AbstractApiBase {}

  @RestController
  static class HealthController {
    @GetMapping("/health")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    void health() {}
  }
}
