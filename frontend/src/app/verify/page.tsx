import type { Metadata } from "next";
import AuthCard from "./card";

export const metadata: Metadata = {
  title: "VikeSesh | Verify Email",
  description: "Connect on campus",
};

export default function Verify() {
  return (
    <main className="min-h-dvh flex flex-col justify-center mx-auto max-w-lg">
      <div className="space-y-6 pb-6 px-4">
        <h1 className="font-heading font-semibold text-2xl text-center">
          Check your Email
        </h1>
        <p>
          You (<span className="text-primary font-semibold">user@uvic.ca</span>)
          have been sent an email with a verification code. Please enter your
          code to join VikeSesh.
        </p>
      </div>
      <AuthCard />
    </main>
  );
}
