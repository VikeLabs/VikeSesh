"use client";

import { Button } from "@/components/ui/button";
import { Field, FieldLabel, FieldSeparator } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
} from "@/components/ui/input-otp";
import { UserRoundKeyIcon, RefreshCwIcon } from "lucide-react";
import { useEffect, useState } from "react";

export default function AuthCard() {
  const [otpValue, setOtpValue] = useState("");
  const [startTime, setStartTime] = useState(0);
  const [nowTime, setNowTime] = useState(0);

  useEffect(() => {
    setStartTime(Math.floor(Date.now() / 1000));
    setNowTime(Math.floor(Date.now() / 1000));

    const interval = setInterval(
      () => setNowTime(Math.floor(Date.now() / 1000)),
      1000,
    );

    return () => {
      clearInterval(interval);
    };
  }, []);

  const refreshDisabled = nowTime - startTime < 60;

  const RefreshButton = () => {
    if (refreshDisabled) {
      const secsRemaining = 60 + startTime - nowTime;
      return (
        <Button variant="outline" size="xs" disabled>
          <RefreshCwIcon />
          Resend Code in <span className="text-primary">{secsRemaining}</span>
          {secsRemaining !== 1 ? " seconds" : " second"}
        </Button>
      );
    }
    return (
      <Button variant="outline" size="xs">
        <RefreshCwIcon />
        Resend Code
      </Button>
    );
  };

  return (
    <Card className="mx-4">
      <CardContent className="space-y-6">
        <Field>
          <div className="flex flex-col gap-2 md:flex-row md:items-center justify-between">
            <FieldLabel htmlFor="otp-verification">
              Verification code
            </FieldLabel>
            <RefreshButton />
          </div>
          <InputOTP
            maxLength={6}
            id="otp-verification"
            required
            value={otpValue}
            onChange={(value) => setOtpValue(value.toLocaleUpperCase())}
          >
            <InputOTPGroup className="font-mono">
              <InputOTPSlot index={0} />
              <InputOTPSlot index={1} />
              <InputOTPSlot index={2} />
              <InputOTPSlot index={3} />
              <InputOTPSlot index={4} />
              <InputOTPSlot index={5} />
            </InputOTPGroup>
          </InputOTP>
        </Field>
        <FieldSeparator className="mb-3" />
        <Field>
          <FieldLabel htmlFor="">New Password</FieldLabel>
          <Input
            id="password"
            name="password"
            type="password"
            placeholder=""
            required
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="">Confirm Password</FieldLabel>
          <Input
            id="password"
            name="password"
            type="password"
            placeholder=""
            required
          />
        </Field>
        <Field>
          <Button type="submit" className="w-full">
            Create Account
          </Button>
        </Field>
        <FieldSeparator className="mb-3">OR</FieldSeparator>
        <Field>
          <Button className="w-full">
            <UserRoundKeyIcon />
            Create Account with Passkey
          </Button>
        </Field>
      </CardContent>
    </Card>
  );
}
