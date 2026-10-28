package com.unicornfroyo.examples.widgets;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

public final class GetWidgetsApplicationTest {
  private final GetWidgetsApplication application = new GetWidgetsApplication();
  private final MockMvc mvc =
      MockMvcBuilders.standaloneSetup(new GetWidgetsApplication.WidgetController())
          .addFilters(application.securityHeadersFilter())
          .build();

  @Test
  public void getsWidgets() throws Exception {
    mvc.perform(get("/widgets"))
        .andExpect(status().isAccepted())
        .andExpect(content().json("[]"))
        .andExpect(header().string("X-Frame-Options", "DENY"))
        .andExpect(header().string("X-Content-Type-Options", "nosniff"))
        .andExpect(header().string("Referrer-Policy", "no-referrer"))
        .andExpect(
            header().string("Permissions-Policy", "camera=(), microphone=(), geolocation=()"))
        .andExpect(header().doesNotExist("Strict-Transport-Security"));
  }
}
