"use client";

import { Button } from "@/components/ui/button";
import {
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldGroup } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog } from "@base-ui/react";
import {
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
} from "@/components/ui/combobox";
import { countries } from "./countries";
import { Combobox } from "@base-ui/react";
import React from "react";

const countryNames = Object.values(countries).map((ctr) =>
  ctr.native === ctr.name ? ctr.name : `${ctr.native} (${ctr.name})`,
);

export function Footer() {
  const emailId = React.useId();
  const countryId = React.useId();
  const schoolId = React.useId();
  return (
    <aside className="flex justify-center w-full py-4 px-4">
      <Dialog.Root>
        <span className="">
          Not a UVic student?{" "}
          <Dialog.Trigger className="underline hover:text-zinc-700">
            Join the newsletter
          </Dialog.Trigger>{" "}
          to hear when VikeSesh comes to your place of learning.
        </span>
        <DialogContent className="sm:max-w-sm">
          <form action="/api/newsletter" method="POST" className="grid gap-4">
            <DialogHeader>
              <DialogTitle>Join the Newsletter</DialogTitle>
              <DialogDescription>
                Enter your email to hear when VikeSesh comes to your place of
                learning!
              </DialogDescription>
            </DialogHeader>
            <FieldGroup>
              <Field>
                <Label htmlFor={emailId}>
                  <span>
                    Email Address <span className="text-destructive">*</span>
                  </span>
                </Label>
                <Input
                  id={emailId}
                  name="email"
                  type="email"
                  placeholder="user@school.edu"
                  required
                />
              </Field>
              <Field>
                <Label htmlFor={countryId}>Country</Label>
                <Combobox.Root
                  id={countryId}
                  name="country"
                  items={countryNames}
                >
                  <ComboboxInput placeholder="Your place of learning" />
                  <ComboboxContent>
                    <ComboboxEmpty>No items found.</ComboboxEmpty>
                    <ComboboxList>
                      {(item) => (
                        <ComboboxItem
                          className="pointer-events-auto"
                          key={item}
                          value={item}
                        >
                          {item}
                        </ComboboxItem>
                      )}
                    </ComboboxList>
                  </ComboboxContent>
                </Combobox.Root>
              </Field>
              <Field>
                <Label htmlFor={schoolId}>School</Label>
                <Input
                  id={schoolId}
                  name="school"
                  placeholder="University of Victoria"
                />
              </Field>
            </FieldGroup>
            <DialogFooter>
              <Dialog.Close
                render={<Button variant="outline">Cancel</Button>}
              />
              <Button type="submit">Save changes</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog.Root>
    </aside>
  );
}
