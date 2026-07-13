`timescale 1ns/1ps
// Property-based testbench: asserts INVARIANTS only, never compares to a golden model.
// Properties:
//   P1 mutex:      grant is onehot0 (at most one bit high)
//   P2 no-empty:   (grant & ~req) == 0  (never grant an idle line)
//   P3 fairness:   a line whose req is held high continuously must get a grant
//                  within FAIR_BOUND (=6) cycles, else starvation -> FAIL.
module property_tb;
  localparam integer N          = 4;
  localparam integer FAIR_BOUND = 6;   // N+2

  reg                clk;
  reg                rst_n;
  reg  [3:0]         req;
  wire [3:0]         grant;

  integer            i;
  integer            errors;
  // per-line consecutive cycles that req has been held high without being granted
  integer            wait_cnt [0:3];
  reg  [3:0]         req_prev;

  // DUT
  arbiter_rr dut (.clk(clk), .rst_n(rst_n), .req(req), .grant(grant));

  // 10ns clock
  initial clk = 1'b0;
  always #5 clk = ~clk;

  // ---- helper: onehot0 check (at most one bit set) ----
  function automatic is_onehot0;
    input [3:0] v;
    begin
      is_onehot0 = ((v & (v - 4'b0001)) == 4'b0000); // clears lowest set bit; 0 => <=1 bit
    end
  endfunction

  // ---- property checks, evaluated every cycle on sampled grant ----
  task check_properties;
    begin
      // P1 mutual exclusion
      if (!is_onehot0(grant)) begin
        $display("FAILED: P1 mutex violated at time %0t, grant=%b", $time, grant);
        errors = errors + 1;
      end
      // P2 no empty grant
      if ((grant & ~req) != 4'b0000) begin
        $display("FAILED: P2 empty-grant violated at time %0t, req=%b grant=%b",
                 $time, req, grant);
        errors = errors + 1;
      end
      // P3 fairness bookkeeping: update per-line wait counters
      for (i = 0; i < N; i = i + 1) begin
        if (req[i] === 1'b1 && (req_prev[i] === 1'b1)) begin
          // req held high across this cycle
          if (grant[i] === 1'b1) begin
            wait_cnt[i] = 0;               // served -> reset
          end else begin
            wait_cnt[i] = wait_cnt[i] + 1; // still waiting
            if (wait_cnt[i] > FAIR_BOUND) begin
              $display("FAILED: P3 fairness/starvation on line %0d at time %0t (waited %0d cycles), req=%b grant=%b",
                       i, $time, wait_cnt[i], req, grant);
              errors = errors + 1;
            end
          end
        end else begin
          // req not continuously held -> restart the window, count this cycle if granted
          wait_cnt[i] = (grant[i] === 1'b1) ? 0 : 0;
        end
      end
      req_prev = req;
    end
  endtask

  // sample slightly after the rising edge so registered grant is settled
  always @(posedge clk) begin
    #1;
    if (rst_n) check_properties;
  end

  // ---- stimulus ----
  integer k;
  integer seed;
  initial begin
    errors   = 0;
    req      = 4'b0000;
    req_prev = 4'b0000;
    rst_n    = 1'b0;
    seed     = 32'hC0FFEE;
    for (i = 0; i < N; i = i + 1) wait_cnt[i] = 0;

    // hold reset a few cycles
    repeat (3) @(posedge clk);
    @(negedge clk);
    rst_n = 1'b1;

    // ---- Directed 1: all req high held long -> exercises rotation & fairness ----
    req = 4'b1111;
    repeat (20) @(negedge clk);

    // ---- Directed 2: only high-index lines held (kills fixed-priority arbiters) ----
    req = 4'b1110;   // lines 1,2,3 held; a low-prio-first fixed arbiter starves 2,3
    repeat (20) @(negedge clk);

    req = 4'b1010;   // lines 1,3 held
    repeat (20) @(negedge clk);

    req = 4'b1000;   // only line 3 held; fixed-priority-low would starve it vs others? single line must be served
    repeat (12) @(negedge clk);

    // ---- Directed 3: rotating single requests ----
    req = 4'b0001; repeat (4) @(negedge clk);
    req = 4'b0010; repeat (4) @(negedge clk);
    req = 4'b0100; repeat (4) @(negedge clk);
    req = 4'b1000; repeat (4) @(negedge clk);

    // ---- Directed 4: pairs and gaps ----
    req = 4'b0110; repeat (16) @(negedge clk);
    req = 4'b1100; repeat (16) @(negedge clk);
    req = 4'b0101; repeat (16) @(negedge clk);

    // ---- Random stimulus (with stretches of held requests for fairness) ----
    for (k = 0; k < 400; k = k + 1) begin
      // bias toward holding requests so fairness window can build up
      if (($random(seed) % 3) == 0)
        req = $random(seed);            // change request set
      // else keep same req (held) -> stresses starvation detection
      @(negedge clk);
    end

    // ---- Random held-high bursts: pick a fixed mask and hold many cycles ----
    for (k = 0; k < 8; k = k + 1) begin
      req = $random(seed) & 4'b1111;
      if (req == 4'b0000) req = 4'b1111;
      repeat (12) @(negedge clk);
    end

    req = 4'b0000;
    repeat (5) @(negedge clk);

    if (errors == 0)
      $display("PASSED: all properties (mutex, no-empty-grant, fairness) held over the run.");
    else
      $display("FAILED: %0d property violation(s) detected.", errors);

    $finish;
  end

  // safety timeout
  initial begin
    #200000;
    $display("FAILED: timeout (simulation did not finish)");
    $finish;
  end
endmodule