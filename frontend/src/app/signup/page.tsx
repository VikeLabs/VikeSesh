import { Metadata } from "next";
import { Footer } from "./footer";
import uvicIcon from "@/assets/uvic-2.svg";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";

export const metadata: Metadata = {
  title: "VikeSesh | Sign Up",
  description: "Connect on campus",
};

export default function Signup() {
  return (
    <main className="min-h-dvh flex flex-col">
      <div className="flex flex-col md:flex-row flex-1 items-center gap-16 md:justify-between px-16">
        <div className="space-y-8">
          <div className="size-16 rounded-full bg-primary-700"></div>
          <h1 className="text-5xl font-heading font-medium">Create Account</h1>
          <p className="text-2xl max-w-md font-heading font-medium">
            A{" "}
            <Image
              src={uvicIcon}
              alt=""
              className="h-6 pb-1 pr-1 w-min inline align-middle"
            />
            UVic email address (
            <span className="text-zinc-700">
              user<span className="font-bold">@uvic.ca</span>
            </span>
            ) is required to use VikeSesh.
          </p>
        </div>
        <form action="/api/verify-email" className="min-w-sm px-4 md:min-w-md">
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="email">Email Address</FieldLabel>
              <Input
                id="email"
                name="email"
                type="email"
                placeholder="user@uvic.ca"
                required
              />
            </Field>
            <Field>
              <Button type="submit">Verify Email</Button>
            </Field>
          </FieldGroup>
        </form>
      </div>
      <Footer />
    </main>
  );
}
