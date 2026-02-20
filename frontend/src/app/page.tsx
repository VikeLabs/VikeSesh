import vikelabs from "@/assets/vikelabs.png";
import placeholderUnsplash from "@/assets/placeholder-unsplash.jpg";
import { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";

export const metadata: Metadata = {
  title: "VikeSesh",
  description: "Connect on campus",
};

export default function Home() {
  return (
    <main className="min-h-dvh flex flex-col">
      <div className="flex flex-1 items-center justify-between overflow-x-hidden">
        <div className="pl-16 space-y-8">
          <h1 className="text-5xl font-heading font-medium">
            Connect on Campus
          </h1>
          <p className="text-2xl max-w-md font-heading font-medium">
            From study groups to bar crawls, find your community with VikeSesh.
          </p>
          <div className="flex gap-4">
            <Link
              className="bg-primary-700 px-6 py-3 rounded-lg text-xl text-white font-medium"
              href="/signup"
            >
              Get Started
            </Link>
            <Link
              className="border-2 border-zinc-700 px-6 py-3 rounded-lg text-xl font-medium"
              href="/login"
            >
              Log In
            </Link>
          </div>
        </div>
        <div
          className={`-mr-16 border-2 border-zinc-700 drop-shadow-lg rounded-3xl max-w-lg p-4 overflow-hidden`}
        >
          <div
            className={`border-2 border-zinc-700 rounded-xl overflow-hidden`}
          >
            <Image src={placeholderUnsplash} alt="" className="object-cover" />
          </div>
        </div>
      </div>
      <aside className="flex justify-center w-full bg-[#FFF6B6] border-t-2 border-[#AE9A00] py-3">
        <span className="flex items-center text-xl font-heading font-medium gap-2">
          <span>A</span>
          <Link href="https://vikelabs.ca" className="flex items-center gap-1">
            <Image src={vikelabs} alt="The VikeLabs logo" className="size-8" />
            <span className="font-bold">VIKELABS</span>
          </Link>
          <span>Project</span>
        </span>
      </aside>
    </main>
  );
}
